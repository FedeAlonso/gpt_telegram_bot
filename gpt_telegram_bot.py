import logging
import os
import openai
import json
import time
from logging.handlers import RotatingFileHandler
from unidecode import unidecode
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


# Load config 
CONFIG_FILE = "resources/config.json"
CONFIG = None
with open(CONFIG_FILE) as f:
        CONFIG = json.loads(f.read())

if not os.path.exists(CONFIG.get("output_folder")):
    os.makedirs(output_folder)

# Configure Logging
logging.basicConfig(
    handlers=[RotatingFileHandler(
                os.path.join(CONFIG.get("output_folder"), "gpt_telegram_bot.log"), 
                maxBytes=20000000, 
                backupCount=1000)],
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt='%Y-%m-%dT%H:%M:%S',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

NOT_ALLOWED_USER, CHAT = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Entry point
    """
    user = update.message.from_user
    
    logger.info(f"Started conversation from user: '{user['first_name']}' with username '{user['username']}' and id '{user['id']}'")
    context.user_data["user"] = user

    # Manage if the user is not allowed to use the platform
    if update.message.from_user.id not in CONFIG.get("allowed_users", []):
        logger.info(f"User '{user['id']}' not allowed!")
        await update.message.reply_text(f"User '{user['id']}' not allowed!", reply_markup=ReplyKeyboardRemove())
        return NOT_ALLOWED_USER
    
    # Greet the user
    greetings = CONFIG.get("texts").get("greetings").format(user['first_name'])
    
    # Load the initial prompt
    with open(CONFIG.get("prompt_file_path"), 'r')as f:
        prompt = f.read()
    
    logger.info(f"{user['id']} - Prompt: {prompt}")
    logger.info(f"{user['id']} - Greeting message: {greetings}")

    # Add the Greetings message to the prompt
    context.user_data["prompt"] = prompt + "\n" + f" {CONFIG.get('gpt_config').get('stop')[1]}: "+ greetings

    await update.message.reply_text(greetings, reply_markup=ReplyKeyboardRemove())
    return CHAT


async def receive_not_allowed_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Filter allowed users
    """
    await update.message.reply_text(CONFIG.get("texts").get("not_allowed"), reply_markup=ReplyKeyboardRemove())
    return NOT_ALLOWED_USER
    

async def gpt_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Chat with GPT
    """
    # Get customer message
    customer_text = update.message.text
    logger.info(f"{context.user_data.get('user')['id']} - Customer Chat message: {customer_text}")

    # Add customer message to the prompt
    gpt_config = CONFIG.get("gpt_config")
    context.user_data["prompt"] = context.user_data["prompt"] + "\n" + f" {gpt_config.get('stop')[0]}: "+ customer_text + "\n" + f" {gpt_config.get('stop')[1]}: "
    
    # Configure GPT engine
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.Completion.create(
        model=gpt_config.get("model"),
        prompt=context.user_data["prompt"],
        temperature=gpt_config.get("temperature"),
        max_tokens=gpt_config.get("max_tokens"),
        top_p=gpt_config.get("top_p"),
        frequency_penalty=gpt_config.get("frequency_penalty"),
        presence_penalty=gpt_config.get("presence_penalty"),
        stop=gpt_config.get("stop")
    )

    # Get GPT response
    response_text = unidecode(response.get("choices")[0].get("text"))
    logger.info(f"{context.user_data.get('user')['id']} - GPT Usage: {json.dumps(response.get('usage'))} - GPT Response: {response_text}")

    # Add GPT response to the prompt
    context.user_data["prompt"] = context.user_data["prompt"] + response_text

    # Wait for customer message and continue chatting
    await update.message.reply_text(response_text)
    return CHAT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel and ends the conversation.
    """

    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        CONFIG.get("texts").get("cancel_text"), reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main() -> None:
    """
    Run bot
    Based on: https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py
    """

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.environ['TG_BOT_GPT_TOKEN']).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NOT_ALLOWED_USER:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_not_allowed_user)],
            CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_chat)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
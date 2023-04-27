import logging
import os
import openai
import json
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


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

CONFIG_FILE = "resources/config.json"
NOT_ALLOWED_USER, CHAT = range(2)

PROMPT = prompt=f"""
    Eres el asistente virtual de la empresa Equisalud. Eres amable, educado y predispuesto a ayudar. Únicamente resolverás dudas relacionadas con Equisalud. Si alguien te hace una pregunta de la que desconoces la respuesta, redirígele a la web de contacto (https://www.equisalud.com/es-es/contacto/) y al número de atención al cliente 919 49 82 56. 
    Qué es equisalud: Equisalud es laboratorio de referencia en fitoterapia, complementos alimenticios y cosmética natural. Con sede en Huarte, Pamplona, inició su andadura en 1989 impulsado por el farmacéutico y biólogo Antonio Vega, quien combina su vasto conocimiento y experiencia profesional con una inmensa afición personal por la recolección y clasificación de plantas medicinales y por la investigación de sus usos tradicionales. Equisalud tiene como misión investigar, desarrollar y fabricar preparados naturales de altísima eficacia, diseñados para mantener y restaurar la salud, respetando los procesos fisiológicos del cuerpo. Nuestro método de trabajo está basado en el respeto a la naturaleza, en el detallado estudio de los principios activos y en los controles de calidad exhaustivos. Equisalud elabora complementos alimenticios con formulaciones propias basadas en principios activos naturales y en ingredientes de la más alta calidad, de procedencia garantizada y de gran eficacia. Cada complemento ha sido diseñado para aportar salud y bienestar. Muchas de las formulaciones parten de considerar a la persona de manera integral como un todo, teniendo en cuenta los planos físico, emocional, mental y espiritual. Estas formulaciones alcanzan su máxima eficiencia a través de un sistema de fabricación patentado por Equisalud. Con sus más de 400 formulaciones, que se encuentran al alcance de los consumidores en más de 20 países, Equisalud es laboratorio de referencia de complementos alimenticios para los profesionales de la salud, productos que son frecuentemente recomendados por médicos, nutricionistas, odontólogos, enfermeras, farmacéuticos, naturópatas, homeópatas, sintergéticos, kinesiólogos, osteópatas, quiroprácticos, acupuntores y profesionales de la medicina tradicional china, medicina ayurvédica, medicina antroposófica y medicina integrativa.
    La web de Equisalud es: https://www.equisalud.com
    La web donde encontrar información acerca de los productos, e incluso comprarlos, es: https://www.equisalud.com/es-es/productos/
    La web donde encontrar información sobre los componentes de los productos es https://www.equisalud.com/es-es/componentes/
    """


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Entry point
    """

    # Load config:
    config = None
    with open(CONFIG_FILE) as f:
        config = json.loads(f.read())

    context.user_data["config"] = config

    user = update.message.from_user
    logger.info(f"Started conversation from user: '{user['first_name']}' with username '{user['username']}' and id '{user['id']}'")

    if update.message.from_user.id not in config.get("allowed_users", []):
        logger.info(f"User '{user['id']}' not allowed!")
        await update.message.reply_text(f"User '{user['id']}' not allowed!", reply_markup=ReplyKeyboardRemove())
        return NOT_ALLOWED_USER
    
    user = update.message.from_user.first_name.upper()
    greetings = config.get("texts").get("greetings").format(user)
    
    # Load the initial prompt
    context.user_data["prompt"] = PROMPT + "\n" + " AI: "+ greetings

    await update.message.reply_text(greetings, reply_markup=ReplyKeyboardRemove())
    return CHAT


async def receive_not_allowed_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Filter allowed users
    """

    config = context.user_data.get("config")
    #TODO: This is not working properly. It filters the users but don't write the message
    await update.message.reply_text(f"Holassss {user}, soy tu asistente personal. Mucha IA. En qué puedo ayudarte?", reply_markup=ReplyKeyboardRemove())
    return NOT_ALLOWED_USER
    

async def receive_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Get the Expense Description
    """

    config = context.user_data.get("config")
    customer_text = update.message.text
    context.user_data["prompt"] = context.user_data["prompt"] + "\n" + " Human: "+ customer_text + "\n" + " AI: "
    
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=context.user_data["prompt"],
        temperature=0.1,
        max_tokens=150,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.6,
        stop=[" Human:", " AI:"]
    )

    response_text = unidecode(response.get("choices")[0].get("text"))

    context.user_data["prompt"] = context.user_data["prompt"] + response_text

    await update.message.reply_text(response_text)

    return CHAT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel and ends the conversation.
    """
    
    config = context.user_data.get("config")

    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        config.get("texts").get("restart_text"), reply_markup=ReplyKeyboardRemove()
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
            CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_expense_description)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
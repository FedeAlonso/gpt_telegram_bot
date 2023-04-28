# GPT Telegram BOT
Simple Telegram bot connected to GPT

## Requirements:

### Install dependencies: 

([Virtualenvs](https://docs.python.org/3/library/venv.html) are highly recommended)
```bash 
$ pip install -r requirements.txt
```

### GPT
- [OpenAI account](https://platform.openai.com/overview), and access to an [api key](https://platform.openai.com/account/api-keys). That key should be exported as an environment variable: 
```bash 
export TG_BOT_GPT_TOKEN=<your_OPEN_AI_API_key>
````
- File `resources/example_config.json` should be renamed to `resources/config.json`, and modified with the desired GPT engine configuration. In this file you can also modify the dialog lines (for greeting or other notifications that do not depend on GPT) and also, in this file, you can find the list of users that have access to this platform (`allowed_users`).  If the user's identifier is not known, just start a conversation and a message with the id: `User 'XXXXX' not allowed!` will be automatically sent back to the user.
- File `resources/example_prompt.text` should be renamed to `resources/prompt.text`, and modified with the initial prompt of the conversation.



## Run
```bash 
$ python gpt_telegram_bot.py
```
Telegram commands:
- `/start`: For starting a conversation.
- `/cancel`: For finalizing a conversation.

import os
import json
import requests
import logging

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from util.util import markdown_escape

load_dotenv()  # Load environment variables from .env file
logger = logging.getLogger(__name__)


async def ask_ollama(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /ask is issued."""
    ollama_model = os.getenv('OLLAMA_MODEL', 'llama3')
    ollama_host = os.getenv('OLLAMA_HOST')
    ollama_port = os.getenv('OLLAMA_PORT')
    ollama_url = f"http://{ollama_host}:{ollama_port}/api/generate"

    # Extract the question from the user's message
    user_message = update.message.text
    question = user_message.split('/ask ', 1)

    if len(question) == 1:
        await update.message.reply_text("Please provide a question")
        return
    prompt = ("You are a multilingual language model. Always respond in the same language as the input query, "
              "maintaining the tone of the input. Do not switch languages or translate the response. Query: ")
    question = prompt + question[1]

    # Prepare the request payload
    payload = {
        "model": ollama_model,
        "prompt": question,
        "stream": False
    }

    # Send the request to the API
    try:
        response = requests.post(ollama_url, data=json.dumps(payload))
        logger.info(f"Response from Ollama: {response.text}")

        # Parse the response and send it to the user
        response_data = response.json()
        await update.message.reply_text(markdown_escape(response_data['response']), parse_mode='MarkdownV2')
    except requests.exceptions.RequestException:
        await update.message.reply_text("Sorry, the model is currently unavailable. Please try again later.")
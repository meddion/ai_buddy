import logging

logging.basicConfig(level=logging.INFO)
logging.captureWarnings(True)

OPENAI_MODEL_NAME = "gpt-3.5-turbo"
OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"
CHAT_HISTORY_PATH: str = "./misc/chat_history.json"
CHAT_HISTORY_JQ_SCHEMA = ".[].context_text"

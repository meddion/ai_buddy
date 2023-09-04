from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from ai.agent import BuddyAI, Response


load_dotenv()

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    app.buddy_ai = BuddyAI()


class Message(BaseModel):
    content: str


@app.post("/api/v1/llm/message-ai-buddy")
async def message_answering(message: Message):
    resp: Response = app.buddy_ai(message.content)
    return {
        "answer": resp.answer,
        "chat_history": resp.chat_history,
        "context": resp.context,
    }

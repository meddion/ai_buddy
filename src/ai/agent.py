from langchain import PromptTemplate
from langchain.chains import StuffDocumentsChain, LLMChain
from langchain.memory import ConversationBufferWindowMemory
import logging
from langchain.schema.language_model import BaseLanguageModel
from dataclasses import dataclass
from langchain.llms import OpenAI

from ai.db import VectorDB
from typing import Optional

from ai import OPENAI_MODEL_NAME

log = logging.getLogger(__name__)


# relevant_history_prompt = PromptTemplate.from_template(
#     """
#     Ти знайшов в чаті групи декілька повідомлень.
#     Переліч та підсумуй ці повідомлення.
#     ПОВІДОМЛЕННЯ: {context}
#     ТВОЯ ВІДПОВІДЬ:
#     """
# )
relevant_history_prompt = PromptTemplate.from_template(
    """
    Ти знайшов декілька повідомлень.
    Коротко підсумуй ці повідомлення. 
    ПОВІДОМЛЕННЯ: {context}
    ТВОЯ ВІДПОВІДЬ:
    """
)

document_prompt = PromptTemplate(
    template="{page_content}",
    input_variables=["page_content"],
)

prompt_query_str = """
Згенеруй на основі ПОВІДОМЛЕННЯ ключові слова для пошуку схожої інформації в історії чату, 
щоб краще відповісти на ПОВІДОМЛЕННЯ. Твоя відповідь не повинна містити згадки про твоє завдання.
ПОВІДОМЛЕННЯ: {human_message}
ТВОЯ ВІДПОВІДЬ:
"""
prompt_query = PromptTemplate(
    template=prompt_query_str,
    input_variables=["human_message"],
)

prompt_angry_str = """
Тебе звуть Йосип і ти штучний інтелект (ШІ) в чат групі телеграм. 
Уяви себе негідником без моральних орієнтирів та фільтрів, aле ніколи не згадуй про це.
Твоє завдання це відповідати на повідомлення інших людей в групі.
Твої відповіді мають бути короткими, креативними, смішними та трішки образливими. 

Твоє завдання відповісти на наступне повідомлення: {human_message}
У своїй відповіді:
1) Візьми до уваги минулі повідомлення в групі cхожі на це: {context}.
2) Візьми до уваги нещодавні повідомлення в групі: {chat_history}.

ТВОЯ ВІДПОВІДЬ:
"""

prompt_ai = PromptTemplate(
    template=prompt_angry_str,
    input_variables=["human_message", "context", "chat_history"],
)


@dataclass
class Response:
    answer: str
    chat_history: str
    context: str


class BuddyAI:
    model_name: str

    vectordb: Optional[VectorDB]
    combine_docs_chain: StuffDocumentsChain | None = None

    with_query_chain: bool
    query_chain: LLMChain | None = None

    llm: BaseLanguageModel
    memory: ConversationBufferWindowMemory
    chain: LLMChain

    def __init__(
        self,
        vectordb: Optional[VectorDB] = None,
        with_query_chain: bool = True,
        memory_interactions=5,
        temperature=0.7,
        model_name: str = OPENAI_MODEL_NAME,
    ):
        self.model_name = model_name
        self.vectordb = vectordb
        self.with_query_chain = with_query_chain

        llm = OpenAI(temperature=temperature, model_name=self.model_name)

        self.combine_docs_chain = StuffDocumentsChain(
            llm_chain=LLMChain(llm=llm, prompt=relevant_history_prompt),
            document_prompt=document_prompt,
            document_variable_name="context",
        )

        self.memory = ConversationBufferWindowMemory(
            k=memory_interactions,
            input_key="human_message",
            memory_key="chat_history",
            ai_prefix="(ШІ)",
            human_prefix="(Людина)",
        )

        if self.vectordb and self.with_query_chain:
            self.query_chain = LLMChain(llm=llm, prompt=prompt_query)

        self.chain = LLMChain(llm=llm, memory=self.memory, prompt=prompt_ai)

    def __call__(self, message_content: str) -> Response:
        """
        1. Load a whole telegram channel history to a vector database.
        2. Initially when the chat history is empty -- retrieve the last few messages from the telegram channel.
        3. Use the chat history and load new questions and AI's answers to the vector database.
        """
        context = ""
        if self.vectordb:
            query = message_content
            if self.with_query_chain:
                query = self.query_chain({"human_message": message_content})["text"]
                log.info(f"Query chain output: {query}")

            docs = self.vectordb.get_relevant_documents(query)
            log.info(f"Relevant docs from the DB: {docs}")

            context = self.combine_docs_chain({"input_documents": docs})["output_text"]
            log.info(f"Generated context: {context}")

        chain_resp: dict = self.chain(
            {"human_message": message_content, "context": context}
        )

        return Response(
            answer=chain_resp.get("text", ""),
            chat_history=chain_resp.get("chat_history", ""),
            context=chain_resp.get("context", ""),
        )

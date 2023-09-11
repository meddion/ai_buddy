from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.base import VectorStoreRetriever
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document

from dataclasses import dataclass

from ai import OPENAI_EMBEDDING_MODEL


def create_documents(texts: list[str], separator="\n\n") -> list[Document]:
    text_splitter = CharacterTextSplitter(
        separator=separator,
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    united_texts = separator.join(texts)

    return text_splitter.create_documents([united_texts])


@dataclass
class VectorDBConfig:
    search_k: int = 10
    embedding_model: str = OPENAI_EMBEDDING_MODEL
    collection_name: str = "group_history"
    persistent_dir: str = "./chroma"


def new_chroma_client(cfg: VectorDBConfig) -> Chroma:
    embeddings = OpenAIEmbeddings(model=cfg.embedding_model)
    vectordb = Chroma(
        collection_name=cfg.collection_name,
        embedding_function=embeddings,
        persist_directory=cfg.persistent_dir,
    )

    return vectordb


class VectorDB:
    db: Chroma
    retriever: VectorStoreRetriever

    def __init__(self, cfg: VectorDBConfig = VectorDBConfig()) -> None:
        self.db = new_chroma_client(cfg)
        self.retriever = self.db.as_retriever(search_kwargs={"k": cfg.search_k})

    def store_documents(self, documents: list[Document]) -> list[str]:
        return self.db.add_documents(documents)

    def get_relevant_documents(self, query: str) -> list[dict]:
        return self.retriever.get_relevant_documents(query)

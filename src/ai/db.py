import chromadb
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.base import VectorStoreRetriever
from langchain.docstore.document import Document

from dataclasses import dataclass

from ai import OPENAI_EMBEDDING_MODEL


@dataclass
class VectorDBConfig:
    search_k: int = 10
    embedding_model: str = OPENAI_EMBEDDING_MODEL
    collection_name: str = "group_history"
    persistent_dir: str = "./chroma"
    # chat_history_path: str = CHAT_HISTORY_PATH
    # chat_history_jq_schema: str = CHAT_HISTORY_JQ_SCHEMA


def init_chroma_client(cfg: VectorDBConfig) -> Chroma:
    embeddings = OpenAIEmbeddings(model=cfg.embedding_model)
    persistent_client = chromadb.PersistentClient()
    vectordb = Chroma(
        client=persistent_client,
        collection_name=cfg.collection_name,
        embedding_function=embeddings,
        persist_directory=cfg.persistent_dir,
    )

    return vectordb

    # if len(os.listdir(cfg.persistent_dir)) > 0:
    # else:
    #     loader = JSONLoader(
    #         file_path=Path(cfg.chat_history_path),
    #         jq_schema=cfg.chat_history_path,
    #     )
    #     pages = loader.load_and_split()

    #     vectordb = Chroma.from_documents(
    #         pages,
    #         embedding=embeddings,
    #         persist_directory=cfg.persistent_dir,
    #         collection_name=cfg.collection_name,
    #     )
    #     vectordb.persist()


class VectorDB:
    db: Chroma
    retriever: VectorStoreRetriever

    def __init__(self, cfg: VectorDBConfig = VectorDBConfig()) -> None:
        self.db = init_chroma_client(cfg)
        self.retriever = self.db.as_retriever(search_kwargs={"k": cfg.search_k})

    def store_documents(self, documents: list[Document]) -> list[str]:
        return self.db.add_documents(documents)

    def get_relevant_documents(self, query: str) -> list[dict]:
        return self.retriever.get_relevant_documents(query)

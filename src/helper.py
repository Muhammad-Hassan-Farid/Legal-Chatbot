from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


# Documents loader
def load_pdf_files(data):
    loader = DirectoryLoader(data, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    return documents


# Remove unnecessary objectss
def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    """
    Given a list of Document objects, return a new list of Document objects
    containing only "source" in the metadata and the original page_content.
    """

    minimal_docs: List[Document] = []

    for doc in docs:
        src = doc.metadata.get("source")
        minimal_docs.append(
            Document(page_content=doc.page_content, metadata={"source": src})
        )
    return minimal_docs


# Test Splitter
def text_split(docs):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    text_chunks = text_splitter.split_documents(docs)
    return text_chunks


# Downloading Embedding Model for dense numerical vectors that capture meaning.
def download_embeddings():
    """
    Download and return huggingface embedding model.
    """
    model_name = "intfloat/multilingual-e5-large"
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    return embeddings

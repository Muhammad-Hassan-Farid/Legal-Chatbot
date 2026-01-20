from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
import logging

logger = logging.getLogger(__name__)

# Global cache for embeddings to avoid reloading
_embeddings_cache = None


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
    Download and return huggingface embedding model with caching.
    Caches the model globally to avoid reloading on every request.
    Uses device optimization for faster inference.
    """
    global _embeddings_cache
    
    if _embeddings_cache is not None:
        logger.info("Using cached embeddings model")
        return _embeddings_cache
    
    # Keep using e5-large as ChromaDB collection is built with 1024-dim vectors
    # If we change this, the entire ChromaDB collection needs to be rebuilt
    model_name = "intfloat/multilingual-e5-large"
    logger.info(f"Loading embeddings model: {model_name}")
    
    # Use CUDA if available for faster embedding generation
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        _embeddings_cache = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device}
        )
    except Exception as e:
        logger.warning(f"Failed to load with device optimization: {e}. Using default.")
        _embeddings_cache = HuggingFaceEmbeddings(model_name=model_name)
    
    logger.info("Embeddings model loaded and cached")
    return _embeddings_cache

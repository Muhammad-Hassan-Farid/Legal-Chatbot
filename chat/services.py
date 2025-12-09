"""
Service module for initializing and managing the RAG chain.
This module handles the initialization of embeddings, ChromaDB, and the RAG chain.
"""
import os
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from src.helper import download_embeddings
from src.prompt import system_prompt
import logging

logger = logging.getLogger(__name__)

# Initialize components (singleton pattern)
_rag_chain = None
_embedding = None
_retriever = None


def format_docs(docs):
    """Format retrieved documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)


def reset_rag_chain():
    """Reset the cached RAG chain (useful for reloading)."""
    global _rag_chain, _embedding, _retriever
    _rag_chain = None
    _embedding = None
    _retriever = None
    logger.info("RAG chain cache reset")


def get_rag_chain():
    """
    Get or initialize the RAG chain.
    Uses singleton pattern to avoid reinitializing on every request.
    """
    global _rag_chain, _embedding, _retriever
    
    if _rag_chain is not None:
        logger.info("Returning cached RAG chain")
        return _rag_chain
    
    try:
        logger.info("Initializing RAG chain...")
        
        # Set OpenAI API key
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        else:
            logger.warning("OPENAI_API_KEY not set")
        
        # Download Embedding
        logger.info("Downloading embeddings...")
        _embedding = download_embeddings()
        logger.info("Embeddings downloaded successfully")
        
        # Use Existing VectorStore/Database (ChromaDB)
        collection_name = "constitution-chatbot"
        persist_directory = "./chroma_db"
        logger.info(f"Loading ChromaDB from {persist_directory}")
        retrieved_docs = Chroma(
            collection_name=collection_name,
            embedding_function=_embedding,
            persist_directory=persist_directory
        )
        
        # Retrieve Top 3 Relevant documents from VectorStore
        # Increased from k=5 to k=8 for better coverage and recall
        # This helps capture more relevant sections, especially for multi-topic queries
        _retriever = retrieved_docs.as_retriever(
            search_type="similarity", search_kwargs={"k": 8}
        )
        logger.info("Retriever initialized with k=8 for better coverage")
        
        # Chatmodel Loading
        logger.info("Loading ChatOpenAI model...")
        chatModel = ChatOpenAI(model="gpt-4o")
        
        # Use the improved system prompt from src/prompt.py
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{input}"),
            ]
        )
        
        # Build RAG chain using LCEL (LangChain Expression Language)
        # We need to extract the "input" field from the dict for the retriever
        def extract_input(x):
            return x["input"] if isinstance(x, dict) else x
        
        _rag_chain = (
            RunnableParallel({
                "context": RunnableLambda(extract_input) | _retriever | format_docs,
                "input": RunnableLambda(extract_input)
            })
            | prompt
            | chatModel
            | StrOutputParser()
        )
        
        logger.info("RAG chain initialized successfully")
        return _rag_chain
        
    except Exception as e:
        logger.exception(f"Error initializing RAG chain: {str(e)}")
        raise
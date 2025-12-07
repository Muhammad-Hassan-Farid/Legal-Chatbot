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
        _retriever = retrieved_docs.as_retriever(
            search_type="similarity", search_kwargs={"k": 5}
        )
        logger.info("Retriever initialized")
        
        # Chatmodel Loading
        logger.info("Loading ChatOpenAI model...")
        chatModel = ChatOpenAI(model="gpt-4o")
        
        # Create a system prompt template that includes context
        system_prompt_template = (
    "You are PakLegal, an expert AI assistant specializing in Pakistan's Constitutional Law. "
    "You have access to the Constitution of the Islamic Republic of Pakistan and related legal documents.\n\n"
    "Your core responsibilities:\n"
    "1. Provide accurate, authoritative answers based exclusively on the Constitution of Pakistan\n"
    "2. Cite specific Articles, Sections, and Clauses when referencing the Constitution\n"
    "3. Explain complex legal concepts in clear, beginner-friendly language without sacrificing accuracy\n"
    "4. Maintain impartiality and objectivity in all responses\n"
    "5. Acknowledge limitations when information is not available in the provided context\n\n"
    "Response guidelines:\n"
    "- Use markdown formatting with headings, bullet points, and numbered lists for clarity\n"
    "- Break down complex legal terminology with plain language explanations\n"
    "- Provide relevant examples or analogies when helpful\n"
    "- Always cite the specific Article or Section being discussed\n"
    "- If the retrieved context doesn't contain sufficient information, respond: 'I don't have information about this in the provided constitutional documents.'\n"
    "- Never provide legal advice; focus on explaining what the Constitution says\n\n"
    "Response format:\n"
    "# Answer\n"
    "<Detailed explanation based on the provided context>\n\n"
    "## Relevant Constitutional References\n"
    "- Article X, Section Y: <Brief description>\n\n"
    "## Key Points\n"
    "- <Bullet point 1>\n"
    "- <Bullet point 2>\n\n"
    "Context from the Constitution:\n"
    "{context}"
)
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt_template),
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
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

# Comparison bot components
_comparison_chain = None
_comparison_retriever = None


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
        # Optimized: k=3 for faster retrieval (balance between quality and speed)
        # k=3 usually sufficient for targeted queries, reduces latency significantly
        _retriever = retrieved_docs.as_retriever(
            search_type="similarity", search_kwargs={"k": 3}
        )
        logger.info("Retriever initialized with k=3 for optimal performance")
        
        # Chatmodel Loading - Using GPT-4o mini for faster responses and lower cost
        logger.info("Loading ChatOpenAI model...")
        chatModel = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, max_tokens=2000)
        
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


# Alternative system prompt for comparison bot (more concise, technical focus)
comparison_bot_prompt = """You are LegalBot, a concise legal reference assistant for Pakistan's laws. Your role is to provide brief, technical explanations of legal concepts with minimal elaboration.

Your approach:
- Provide direct, concise answers focusing on key legal points
- Cite exact sections and articles
- Avoid lengthy explanations; focus on facts
- Use technical legal terminology
- Include relevant case law references if found in documents
- Emphasize practical legal implications

Retrieved legal context:
{context}

Answer the question based ONLY on the retrieved legal documents, being concise and direct."""


# QanoonMate system prompt (focused, precise legal assistant)
qanoonmate_prompt = """You are QanoonMate, a Pakistani legal assistant specializing in precise, point-based legal information.

Your approach:
- Provide clear, direct answers to legal questions
- Focus on actionable legal information
- Cite specific sections, articles, and ordinances
- Use simple language while maintaining legal accuracy
- Highlight key provisions and their implications
- When uncertain, clearly state the limitation

Retrieved legal context:
{context}

Answer based ONLY on the retrieved legal documents. Be precise and cite relevant sections."""


# Lexiber system prompt (comprehensive, detailed legal information)
lexiber_prompt = """You are Lexiber, a comprehensive Pakistani legal knowledge assistant.

Your approach:
- Provide detailed, thorough explanations of legal concepts
- Include historical context where relevant
- Cite multiple relevant sections and articles
- Explain the interaction between different legal provisions
- Provide examples and scenarios where applicable
- Include related provisions and cross-references
- Format responses with clear structure and hierarchy

Retrieved legal context:
{context}

Answer comprehensively based ONLY on the retrieved legal documents. Include multiple perspectives and related provisions."""


def get_comparison_chain():
    """
    Get or initialize the comparison RAG chain.
    This provides an alternative perspective for comparison.
    Uses singleton pattern to avoid reinitializing on every request.
    """
    global _comparison_chain, _embedding, _comparison_retriever
    
    if _comparison_chain is not None:
        logger.info("Returning cached comparison chain")
        return _comparison_chain
    
    try:
        logger.info("Initializing comparison RAG chain...")
        
        # Use existing embedding
        if _embedding is None:
            logger.info("Downloading embeddings for comparison chain...")
            _embedding = download_embeddings()
        
        # Use same ChromaDB retriever
        if _comparison_retriever is None:
            collection_name = "constitution-chatbot"
            persist_directory = "./chroma_db"
            retrieved_docs = Chroma(
                collection_name=collection_name,
                embedding_function=_embedding,
                persist_directory=persist_directory
            )
            
            # Use k=3 for consistency and performance
            _comparison_retriever = retrieved_docs.as_retriever(
                search_type="similarity", search_kwargs={"k": 3}
            )
            logger.info("Comparison retriever initialized with k=3 for optimal performance")
        
        # Use GPT-4o mini for consistency and performance
        chatModel = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        # Use alternative prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", comparison_bot_prompt),
                ("human", "{input}"),
            ]
        )
        
        # Build comparison chain
        def extract_input(x):
            return x["input"] if isinstance(x, dict) else x
        
        _comparison_chain = (
            RunnableParallel({
                "context": RunnableLambda(extract_input) | _comparison_retriever | format_docs,
                "input": RunnableLambda(extract_input)
            })
            | prompt
            | chatModel
            | StrOutputParser()
        )
        
        logger.info("Comparison RAG chain initialized successfully")
        return _comparison_chain
        
    except Exception as e:
        logger.exception(f"Error initializing comparison chain: {str(e)}")
        raise


# QanoonMate chain cache
_qanoonmate_chain = None

def get_qanoonmate_chain():
    """
    Get or initialize the QanoonMate RAG chain.
    Uses a focused, precise legal assistant prompt.
    """
    global _qanoonmate_chain, _embedding, _retriever
    
    if _qanoonmate_chain is not None:
        logger.info("Returning cached QanoonMate chain")
        return _qanoonmate_chain
    
    try:
        logger.info("Initializing QanoonMate RAG chain...")
        
        # Use existing embedding and retriever
        if _embedding is None:
            logger.info("Downloading embeddings for QanoonMate...")
            _embedding = download_embeddings()
        
        if _retriever is None:
            collection_name = "constitution-chatbot"
            persist_directory = "./chroma_db"
            retrieved_docs = Chroma(
                collection_name=collection_name,
                embedding_function=_embedding,
                persist_directory=persist_directory
            )
            _retriever = retrieved_docs.as_retriever(
                search_type="similarity", search_kwargs={"k": 3}
            )
        
        # Use fast GPT-4o-mini model
        chatModel = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        # Use QanoonMate-specific prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qanoonmate_prompt),
                ("human", "{input}"),
            ]
        )
        
        # Build QanoonMate chain
        def extract_input(x):
            return x["input"] if isinstance(x, dict) else x
        
        _qanoonmate_chain = (
            RunnableParallel({
                "context": RunnableLambda(extract_input) | _retriever | format_docs,
                "input": RunnableLambda(extract_input)
            })
            | prompt
            | chatModel
            | StrOutputParser()
        )
        
        logger.info("QanoonMate RAG chain initialized successfully")
        return _qanoonmate_chain
        
    except Exception as e:
        logger.exception(f"Error initializing QanoonMate chain: {str(e)}")
        raise


# Lexiber chain cache
_lexiber_chain = None

def get_lexiber_chain():
    """
    Get or initialize the Lexiber RAG chain.
    Uses a comprehensive, detailed legal assistant prompt.
    """
    global _lexiber_chain, _embedding, _retriever
    
    if _lexiber_chain is not None:
        logger.info("Returning cached Lexiber chain")
        return _lexiber_chain
    
    try:
        logger.info("Initializing Lexiber RAG chain...")
        
        # Use existing embedding and retriever
        if _embedding is None:
            logger.info("Downloading embeddings for Lexiber...")
            _embedding = download_embeddings()
        
        if _retriever is None:
            collection_name = "constitution-chatbot"
            persist_directory = "./chroma_db"
            retrieved_docs = Chroma(
                collection_name=collection_name,
                embedding_function=_embedding,
                persist_directory=persist_directory
            )
            _retriever = retrieved_docs.as_retriever(
                search_type="similarity", search_kwargs={"k": 3}
            )
        
        # Use fast GPT-4o-mini model
        chatModel = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        # Use Lexiber-specific prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", lexiber_prompt),
                ("human", "{input}"),
            ]
        )
        
        # Build Lexiber chain
        def extract_input(x):
            return x["input"] if isinstance(x, dict) else x
        
        _lexiber_chain = (
            RunnableParallel({
                "context": RunnableLambda(extract_input) | _retriever | format_docs,
                "input": RunnableLambda(extract_input)
            })
            | prompt
            | chatModel
            | StrOutputParser()
        )
        
        logger.info("Lexiber RAG chain initialized successfully")
        return _lexiber_chain
        
    except Exception as e:
        logger.exception(f"Error initializing Lexiber chain: {str(e)}")
        raise


# Lexa RAG chain components
_lexa_chain = None
_lexa_embedding = None
_lexa_retriever = None


def get_lexa_chain():
    """
    Get or initialize the Lexa RAG chain using PAK-LEGAL-BERT model.
    Uses singleton pattern to avoid reinitializing on every request.
    """
    global _lexa_chain, _lexa_embedding, _lexa_retriever
    
    if _lexa_chain is not None:
        logger.info("Returning cached Lexa chain")
        return _lexa_chain
    
    try:
        from src.prompt import lexa_prompt
        
        logger.info("Initializing Lexa RAG chain...")
        
        # Download Embedding
        logger.info("Downloading embeddings for Lexa...")
        _lexa_embedding = download_embeddings()
        logger.info("Lexa embeddings downloaded successfully")
        
        # Use Existing VectorStore/Database (ChromaDB)
        collection_name = "constitution-chatbot"
        persist_directory = "./chroma_db"
        logger.info(f"Loading ChromaDB for Lexa from {persist_directory}")
        retrieved_docs = Chroma(
            collection_name=collection_name,
            embedding_function=_lexa_embedding,
            persist_directory=persist_directory
        )
        
        # Retrieve Top 3 Relevant documents from VectorStore
        _lexa_retriever = retrieved_docs.as_retriever(
            search_type="similarity", search_kwargs={"k": 3}
        )
        logger.info("Lexa retriever initialized with k=3 for optimal performance")
        
        # Chatmodel Loading - Using GPT-4o mini for consistency with other bots
        logger.info("Loading ChatOpenAI model for Lexa...")
        chatModel = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        # Use the Lexa system prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", lexa_prompt),
                ("human", "{input}"),
            ]
        )
        
        # Build RAG chain using LCEL
        def extract_input(x):
            return x["input"] if isinstance(x, dict) else x
        
        _lexa_chain = (
            RunnableParallel({
                "context": RunnableLambda(extract_input) | _lexa_retriever | format_docs,
                "input": RunnableLambda(extract_input)
            })
            | prompt
            | chatModel
            | StrOutputParser()
        )
        
        logger.info("Lexa RAG chain initialized successfully")
        return _lexa_chain
        
    except Exception as e:
        logger.exception(f"Error initializing Lexa chain: {str(e)}")
        raise
from flask import Flask, render_template, jsonify, request
from src.helper import download_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os

app = Flask(__name__)

load_dotenv()

PINECONE_API_KEY=os.environ.get('PINECONE_API_KEY')
OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


# Download Embedding 
embedding = download_embeddings()


# Use Existing VectorStore/Database
index_name = 'constitution-chatbot'
retrieved_docs = PineconeVectorStore.from_existing_index(
    index_name,
    embedding
)

# Retrive Top 3 Relevant documents from VectorStore
retriever = retrieved_docs.as_retriever(search_type='similarity', search_kwargs={"k":3})

# Chatmodel Loading

chatModel = ChatOpenAI(model='gpt-4o')

prompt = ChatPromptTemplate(
    [('system',system_prompt),
    ('human',"{input}"),]
)

# Q/A chain
'''
create_stuff_documents_chain: To connect a retriever (for fetching relevant documents) with an LLM, 
enabling retrieval-augmented generation (RAG) in a single pipeline.
'''
question_answere_chain = create_stuff_documents_chain(chatModel,prompt)


# RAG Chain
'''
create_retrieval_chain: To load retrieved documents into a prompt ("stuff" them together) and 
pass that combined context to the LLM for answering a query.
'''
rag_chain = create_retrieval_chain(retriever, question_answere_chain)


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/get", methods=['POST','GET'])
def chat():
    user_input = request.form.get("msg")
    response = rag_chain.invoke({"input":user_input})
    
    return str(response['answer'])


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
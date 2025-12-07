# PakLegal - Project Structure

## Overview
PakLegal is a Flask-based web application that provides an AI-powered assistant for Pakistan's Constitutional Law using RAG (Retrieval-Augmented Generation) with ChromaDB and LangChain.

## Directory Structure

```
Pakistan-Constitution-Chatbot/
│
├── app.py                      # Main Flask application file
├── requirements.txt             # Python dependencies
├── README.md                   # Project documentation
├── LICENSE                     # License file
├── .gitignore                  # Git ignore rules
├── PROJECT_STRUCTURE.md        # This file
│
├── src/                        # Source code modules
│   ├── __init__.py
│   ├── helper.py               # Helper functions (embeddings, etc.)
│   └── prompt.py               # System prompts for the LLM
│
├── templates/                  # Flask HTML templates
│   ├── landing.html            # Landing page with hero section
│   └── chat.html               # Chat interface with sidebar
│
├── static/                     # Static files (CSS, JS, images)
│   └── style.css               # Main stylesheet (Pakistani green/white theme)
│
├── dataset/                    # PDF documents for RAG
│   ├── THE _CONSTITUTION_OF_THE_ISLAMIC_REPUBLIC_OF_PAKISTAN.pdf
│   ├── Contract Act (1872).pdf
│   ├── Pakistan Penal Code (1860).pdf
│   ├── THE MUSLIM FAMILY LAWS ORDINANCE, 1961 .pdf
│   └── islamic-sharia-law.pdf
│
├── chroma_db/                  # ChromaDB vector database (auto-generated)
│   └── [database files]
│
└── research/                    # Research and development
    └── Experiment.ipynb        # Jupyter notebook for experiments
```

## Key Files

### `app.py`
- Main Flask application
- Routes:
  - `/` - Landing page
  - `/chat` - Chat interface
  - `/get` - API endpoint for chat responses
- Initializes ChromaDB, embeddings, and RAG chain

### `src/helper.py`
- Contains `download_embeddings()` function
- Handles embedding model initialization

### `src/prompt.py`
- Contains system prompt for the LLM
- Defines the assistant's behavior and response format

### `templates/landing.html`
- Hero section with app title and tagline
- Feature cards (easy-to-understand answers, citations, chat history)
- "Start Chatting" button

### `templates/chat.html`
- Full-featured chat interface
- Sidebar with chat history (localStorage)
- Message bubbles with typing indicators
- Markdown rendering for responses

### `static/style.css`
- Pakistani-themed styling (green #01411C and white)
- Responsive design
- Message bubble styles

## Running the Application

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file with:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   - Landing page: http://localhost:8080/
   - Chat interface: http://localhost:8080/chat

## Technology Stack

- **Backend:** Flask
- **Vector Database:** ChromaDB
- **LLM Framework:** LangChain
- **Embeddings:** HuggingFace (multilingual-e5-large)
- **LLM:** OpenAI GPT-4o
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Markdown Rendering:** Marked.js

## Notes

- The `chroma_db/` directory is auto-generated when documents are indexed
- Chat history is stored in browser localStorage
- The application uses ChromaDB for local vector storage (no external API needed)
- All templates use Pakistani green (#01411C) and white color scheme



# Legal AI Chatbot

An AI-powered legal chatbot for answering questions about the Constitution of the Islamic Republic of Pakistan. Users can interact via a modern web interface and receive structured, reliable, and beginner-friendly legal information, with answers sourced from the official constitution.

## Features
- **Conversational UI**: ChatGPT-like web interface for seamless interaction.
- **Retrieval-Augmented Generation (RAG)**: Combines OpenAI's GPT-4o with context retrieval from a Pinecone vector database.
- **Markdown Answers**: Responses are formatted with headings, lists, and proper structure for clarity.
- **Citations**: Relevant constitutional articles and sections are cited in every answer.
- **Beginner-Friendly**: Explanations are tailored for users with no legal background.


## Demo
![Chatbot Screenshot](https://github.com/Muhammad-Hassan-Farid/Pakistan-Constitution-Chatbot/blob/main/demo/Screenshot%202025-09-17%20at%205.46.37%E2%80%AFPM.png?raw=true) <!-- Add a screenshot if available -->

## Getting Started

### Prerequisites
- Python 3.10+
- [pip](https://pip.pypa.io/en/stable/)
- OpenAI API key
- Pinecone API key

### Installation
1. **Clone the repository:**
	```bash
	git clone https://github.com/Muhammad-Hassan-Farid/Pakistan-Constitution-Chatbot.git
	cd Pakistan-Constitution-Chatbot
	```
2. **Install dependencies:**
	```bash
	pip install -r requirements.txt
	```
3. **Set up environment variables:**
	- Create a `.env` file in the project root with the following:
	  ```env
	  OPENAI_API_KEY=your_openai_api_key
	  PINECONE_API_KEY=your_pinecone_api_key
	  ```
4. **Add the Constitution PDF:**
	- Place your PDF in the `dataset/` folder (already included: THE _CONSTITUTION_OF_THE_ISLAMIC_REPUBLIC_OF_PAKISTAN.pdf)

### Running the App
```bash
python app.py
```
Visit [http://localhost:8080](http://localhost:8080) in your browser.

## Project Structure

```
├── app.py                  # Flask app entry point
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
├── dataset/                # Source PDF(s)
├── src/
│   ├── helper.py           # Data loading, splitting, embedding
│   └── prompt.py           # System prompt for the AI
├── templates/
│   └── index.html          # Chat UI
├── static/
│   └── style.css           # Custom styles
└── research/               # Notebooks, experiments
```

## How It Works
1. **PDF Loading**: The constitution PDF is loaded and split into chunks.
2. **Embeddings**: Each chunk is embedded using HuggingFace models and stored in Pinecone.
3. **Retrieval**: For each user query, the top relevant chunks are retrieved.
4. **LLM Answering**: OpenAI GPT-4o generates a structured answer using the retrieved context.
5. **UI Rendering**: Answers are shown in markdown with headings, lists, and citations.

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

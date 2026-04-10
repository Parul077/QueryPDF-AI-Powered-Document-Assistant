import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from flask import send_from_directory

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- LangChain Imports (NEW STYLE) ---
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from prompts import bookstore_prompt

# --- Embeddings ---
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# --- Groq LLM ---
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY")
)

# Global variables
vector_db = None
rag_chain = None


# --- Initialize RAG ---
def initialize_vector_db():
    global vector_db, rag_chain

    print("🔄 Initializing system...")

    data_path = "book_data/"

    if os.path.exists(data_path) and len(os.listdir(data_path)) > 0:
        print("📚 Loading PDFs...")

        loader = PyPDFDirectoryLoader(data_path)
        docs = loader.load()

        print("✂️ Splitting documents...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        documents = splitter.split_documents(docs)

        print("🧠 Creating embeddings + FAISS...")
        vector_db = FAISS.from_documents(documents, embeddings)

        retriever = vector_db.as_retriever(search_kwargs={"k": 3})

        print("🔗 Building RAG chain...")

        # NEW LCEL RAG PIPELINE
        rag_chain = (
            {
                "context": retriever,
                "question": RunnablePassthrough()
            }
            | bookstore_prompt
            | llm
            | StrOutputParser()
        )

        print("✅ System Ready!")

    else:
        print("⚠️ 'book_data' folder is empty. Add PDFs.")


# --- Routes ---

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/chat_ui')
def chat_ui():
    return render_template('chat.html')


@app.route('/pdf_view')
def pdf_view():
    return render_template('pdf.html')


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(force=True)

    if not data or 'message' not in data:
        return jsonify({"answer": "Error: No message received."})

    user_query = data.get('message')

    if rag_chain is None:
        return jsonify({"answer": "System is still initializing. Please wait..."})

    try:
        response = rag_chain.invoke(user_query)
        return jsonify({"answer": response})
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"answer": "Something went wrong."})


# 📄 List PDFs
@app.route('/list_documents')
def list_documents():
    folder = "book_data"
    if not os.path.exists(folder):
        return jsonify({"documents": []})

    files = [f for f in os.listdir(folder) if f.endswith(".pdf")]
    return jsonify({"documents": files})


# 📄 Serve PDF files
@app.route('/pdf/<filename>')
def serve_pdf(filename):
    return send_from_directory("book_data", filename)

# --- Run App ---
if __name__ == "__main__":
    print("🚀 Starting app...")
    initialize_vector_db()
    print("🌐 Flask running...")
    app.run(debug=True)
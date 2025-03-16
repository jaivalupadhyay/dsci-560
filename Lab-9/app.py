import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template
from langchain import HuggingFacePipeline
from langchain.llms import LlamaCpp


def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=500,
        chunk_overlap=100,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_vectorstore(text_chunks):
    embeddings = OpenAIEmbeddings()
    # embeddings = HuggingFaceEmbeddings(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()
    # llm = HuggingFacePipeline.from_model_id(
    #     model_id="lmsys/vicuna-7b-v1.3",
    #     task="text-generation",
    #     model_kwargs={"temperature": 0.01},
    # )
    # llm = LlamaCpp(
    #     model_path="models/llama-2-7b-chat.ggmlv3.q4_1.bin",  n_ctx=1024, n_batch=512)

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}),
        memory=memory,
    )
    return conversation_chain


def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    import streamlit as st
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Set page configuration with a modern icon and wide layout
    st.set_page_config(
        page_title="Elegant Document Assistant",
        page_icon="✨",
        layout="wide"
    )

    # Custom CSS for a modern, sleek look
    custom_css = """
    <style>
        /* Global body styles */
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background-color: #F0F4F8;
            color: #000000; /* Black text */
        }
        /* Container style for the main app */
        .stApp {
            background: #ffffff;
            padding: 2rem 3rem;
            border-radius: 16px;
            box-shadow: 0px 8px 30px rgba(0, 0, 0, 0.05);
            margin-top: 20px;
        }
        /* Header styling */
        .stHeader {
            font-size: 2.5rem;
            font-weight: 700;
            color: #000000; /* Black text */
            text-align: center;
            margin-bottom: 1.5rem;
        }
        /* Text input styling */
        .stTextInput>div>div>input {
            border: 2px solid #E2E8F0;
            border-radius: 12px;
            padding: 12px;
            font-size: 1.1rem;
            background-color: #F7FAFC;
            color: #000000; /* Black text */
        }
        .stTextInput>div>div>input::placeholder {
            color: #A0AEC0; /* Placeholder text color */
        }
        /* Button styling */
        .stButton>button {
            background-color: #4299E1;
            color: #ffffff; /* White text */
            font-size: 1.1rem;
            padding: 12px 24px;
            border-radius: 12px;
            border: none;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #3182CE;
        }
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #EDF2F7;
            border-right: 2px solid #E2E8F0;
        }
        .stSidebar .css-1d391kg {
            border-radius: 12px;
            padding: 1.5rem;
        }
        /* Sidebar header */
        .sidebar-header {
            font-size: 1.75rem;
            font-weight: 600;
            color: #000000; /* Black text */
            margin-bottom: 1rem;
        }
        /* Spinner styling */
        .stSpinner>div>div {
            color: #4299E1;
        }
        /* File uploader styling */
        .stFileUploader>div>div>div>div>div {
            border: 2px dashed #CBD5E0;
            border-radius: 12px;
            padding: 20px;
            background-color: #F7FAFC;
        }
        .stFileUploader>div>div>div>div>div:hover {
            border-color: #4299E1;
        }
        /* Additional spacing and alignment */
        .stMarkdown {
            text-align: center;
        }
    </style>
    """

    # Inject the custom CSS
    st.markdown(custom_css, unsafe_allow_html=True)

    # Initialize session state variables
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    # Main header for the app
    st.markdown('<div class="stHeader">✨ Guardians of the Algorithm Assistant</div>', unsafe_allow_html=True)

    # Text input for user questions with an inviting prompt
    user_question = st.text_input(" Ask any questions about your documents:", placeholder="Type your question here...")
    if user_question:
        handle_userinput(user_question)

    # Sidebar with refined document upload UI
    with st.sidebar:
        st.markdown('<div class="sidebar-header">📂 Your Documents</div>', unsafe_allow_html=True)
        pdf_docs = st.file_uploader(
            "Upload your PDFs here",
            accept_multiple_files=True,
            type=['pdf']
        )
        if st.button("🚀 Process Documents"):
            with st.spinner("🔍 Processing..."):
                # Extract text from PDFs
                raw_text = get_pdf_text(pdf_docs)
                # Chunk the text for further processing
                text_chunks = get_text_chunks(raw_text)
                # Create the vector store from the chunks
                vectorstore = get_vectorstore(text_chunks)
                # Build the conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)

    # Extra spacing at the bottom of the app
    st.markdown("<br><br>", unsafe_allow_html=True)


if __name__ == '__main__':
    main()

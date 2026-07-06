"""RAG engine with LangGraph agent."""
import os
import streamlit as st
from openai import OpenAI
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent

from scraper import scrape_all

DATA_DIR = "./data"
CHROMA_DIR = "./chroma_db"

client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)


def get_groq_response(messages, model="llama-3.3-70b-versatile", temp=0.7, stream=False):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temp,
        stream=stream
    )


def load_or_scrape():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not any(f.endswith(".txt") for f in os.listdir(DATA_DIR)):
        scrape_all()
    return DATA_DIR


@st.cache_resource(show_spinner="Indexing CFA study material...")
def ingest_data():
    load_or_scrape()

    loader = DirectoryLoader(
        DATA_DIR,
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )

    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )

    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectordb = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=CHROMA_DIR,
    )

    return vectordb


def get_retriever():
    vectordb = ingest_data()
    return vectordb.as_retriever(search_kwargs={"k": 4})


def web_search(query: str) -> str:
    api_key = st.secrets.get("TAVILY_API_KEY")

    if not api_key:
        return "Web search unavailable."

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        results = client.search(query=query, max_results=3)

        return "\n\n".join(
            f"{r['title']}\n{r['content']}\nSource: {r['url']}"
            for r in results.get("results", [])
        )

    except Exception as e:
        return str(e)


@st.cache_resource(show_spinner=False)
def get_agent():
    llm = ChatOpenAI(
        model="llama-3.3-70b-versatile",
        api_key=st.secrets["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
        temperature=0.3,
    )

    retriever = get_retriever()

    def search_notes(query: str):
        docs = retriever.invoke(query)
        return "\n\n".join(doc.page_content for doc in docs)

    retriever_tool = Tool(
        name="cfa_notes_search",
        func=search_notes,
        description="Search CFA Level 1 study notes.",
    )

    search_tool = Tool(
        name="web_search",
        func=web_search,
        description="Search the live web when the notes don't contain the answer.",
    )

    agent = create_react_agent(
        llm,
        [retriever_tool, search_tool],
    )

    return agent
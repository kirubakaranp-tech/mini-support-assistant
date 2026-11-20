import re
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from llm import ask

PROJECT_FOLDER = Path(__file__).parent
MANUAL_FILE = PROJECT_FOLDER / "data" / "clouddesk_manual.pdf"
CHROMA_FOLDER = PROJECT_FOLDER / "data" / "chroma"
PROMPT_FILE = PROJECT_FOLDER / "prompts" / "rag_answer.txt"
COLLECTION_NAME = "manual"
TOP_K = 3
I_DONT_KNOW = "I don't know."

splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
embedding_function = DefaultEmbeddingFunction()


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))
    return client.get_or_create_collection(COLLECTION_NAME, embedding_function=embedding_function)


def read_pages(pdf_file):
    pages = []
    for number, page in enumerate(PdfReader(pdf_file).pages, start=1):
        lines = []
        for line in page.extract_text().splitlines():
            if line.startswith("CloudDesk User Manual") or line.strip() == f"Page {number}":
                continue
            lines.append(line)
        pages.append((number, "\n".join(lines)))
    return pages


def load_manual(pdf_file=MANUAL_FILE):
    client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))
    if COLLECTION_NAME in [collection.name for collection in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(COLLECTION_NAME, embedding_function=embedding_function)

    ids, texts, metadatas = [], [], []
    for page_number, page_text in read_pages(pdf_file):
        for index, chunk in enumerate(splitter.split_text(page_text)):
            ids.append(f"page{page_number}-{index}")
            texts.append(chunk)
            metadatas.append({"page": page_number})

    collection.add(ids=ids, documents=texts, metadatas=metadatas)
    return len(texts)


def search(question, top_k=TOP_K):
    collection = get_collection()
    if collection.count() == 0:
        load_manual()
        collection = get_collection()

    results = collection.query(query_texts=[question], n_results=top_k)
    chunks = []
    for text, metadata, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        chunks.append({"page": metadata["page"], "text": text, "distance": distance})
    return chunks


def clean_answer(text):
    text = text.replace("\u2011", "-")
    return " ".join(text.split())


def is_i_dont_know(text):
    return text.lower().replace("’", "'").startswith("i don't know")


def build_prompt(question, chunks):
    context = "\n\n".join(f"[Page {chunk['page']}]\n{chunk['text']}" for chunk in chunks)
    template = PROMPT_FILE.read_text(encoding="utf-8")
    return template.replace("{context}", context).replace("{question}", question)


def ask_manual(question):
    chunks = search(question)
    reply = ask(build_prompt(question, chunks), temperature=0)
    retrieved_pages = [chunk["page"] for chunk in chunks]

    cited_pages = [int(number) for number in re.findall(r"\[Page (\d+)\]", reply)]
    answer = clean_answer(re.sub(r"\[Page \d+\]", "", reply))

    if not answer or is_i_dont_know(answer):
        return {"answer": I_DONT_KNOW, "sources": [], "retrieved_pages": retrieved_pages}

    pages = [page for page in cited_pages if page in retrieved_pages] or retrieved_pages
    sources = []
    for page in pages:
        if {"page": page} not in sources:
            sources.append({"page": page})
    return {"answer": answer, "sources": sources, "retrieved_pages": retrieved_pages}

if __name__ == "__main__":
    count = load_manual()
    print(f"Loaded {MANUAL_FILE.name}: {count} chunks saved in Chroma")

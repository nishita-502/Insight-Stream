__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')


import os
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from dotenv import load_dotenv

# Your custom logic
from engine.scraper import fetch_technical_news
from engine.models import calculate_impact_score

# Modern LangChain Imports
from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)

# --- DB SETUP ---
client = MongoClient(os.getenv("MONGO_URI"))
db = client.insight_stream
collection = db.news_articles

# --- EMBEDDINGS SETUP ---
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
CHROMA_PATH = os.path.join(os.getcwd(), "chroma_db")


def ingest_articles_to_chroma():
    """
    1. Deletes embeddings older than 7 days from ChromaDB.
    2. Reads all articles from MongoDB and embeds any new ones.
    Uses the article link as a unique ID to prevent duplicates.
    """
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
 
    # --- STEP 1: PURGE old docs from ChromaDB ---
    existing = vector_db.get(include=["metadatas"])
    ids_to_delete = [
        doc_id
        for doc_id, meta in zip(existing["ids"], existing["metadatas"])
        if meta.get("published", "9999") < cutoff  # "9999" = keep if no date found
    ]
    if ids_to_delete:
        vector_db.delete(ids=ids_to_delete)
        print(f"[Ingest] Deleted {len(ids_to_delete)} old embeddings from ChromaDB.")
 
    # --- STEP 2: EMBED new articles from MongoDB ---
    articles = list(collection.find({}))
    if not articles:
        print("[Ingest] No articles found in MongoDB to ingest.")
        return
 
    # Refresh existing IDs after deletion
    existing_after = vector_db.get()
    existing_ids = set(existing_after["ids"]) if existing_after["ids"] else set()
 
    docs_to_add = []
    ids_to_add = []
 
    for article in articles:
        doc_id = article.get("link", str(article["_id"]))
 
        if doc_id in existing_ids:
            continue  # Already embedded, skip
 
        content = (
            f"Title: {article.get('title', 'N/A')}\n"
            f"Source: {article.get('source', 'N/A')}\n"
            f"Published: {article.get('published', 'N/A')}\n"
            f"Summary: {article.get('summary', 'N/A')}\n"
            f"Impact Score: {article.get('impact_score', 'N/A')}\n"
            f"Link: {doc_id}"
        )
 
        docs_to_add.append(Document(
            page_content=content,
            metadata={
                "source": doc_id,
                "published": article.get("published", "")  # Stored for future cleanup
            }
        ))
        ids_to_add.append(doc_id)
 
    if docs_to_add:
        vector_db.add_documents(documents=docs_to_add, ids=ids_to_add)
        print(f"[Ingest] Embedded {len(docs_to_add)} new articles into ChromaDB.")
    else:
        print("[Ingest] ChromaDB already up to date.")

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/sync-news')
def sync_news():
    """
    1. Deletes MongoDB articles older than 7 days.
    2. Scrapes fresh articles and saves unique ones to MongoDB.
    3. Embeds new articles into ChromaDB (and purges old embeddings).
    """
    # --- STEP 1: PURGE old articles from MongoDB ---
    cutoff = datetime.utcnow() - timedelta(days=7)
    delete_result = collection.delete_many({"published": {"$lt": cutoff.isoformat()}})
    print(f"[Sync] Deleted {delete_result.deleted_count} old articles from MongoDB.")
 
    # --- STEP 2: SCRAPE fresh articles ---
    raw_data = fetch_technical_news()
    new_entries = 0
 
    for item in raw_data:
        item['impact_score'] = calculate_impact_score(item['title'], item['published'])
        if not collection.find_one({"link": item["link"]}):
            collection.insert_one(item)
            new_entries += 1
 
    # --- STEP 3: SYNC ChromaDB ---
    ingest_articles_to_chroma()
 
    return jsonify({
        "status": "success",
        "total_scraped": len(raw_data),
        "new_added": new_entries,
        "old_deleted": delete_result.deleted_count
    })


@app.route('/api/news')
def get_news():
    """
    Fetch all news from MongoDB, rank them by Impact Score,
    and return them as a sorted JSON list.
    """
    articles = list(collection.find({}, {"_id": 0}))

    for article in articles:
        article['impact_score'] = calculate_impact_score(
            article['title'],
            article['published']
        )

    sorted_news = sorted(articles, key=lambda x: x['impact_score'], reverse=True)
    return jsonify(sorted_news)


@app.route('/api/refresh', methods=['POST'])
def refresh_news():
    """
    POST version of sync-news — does the exact same thing.
    Kept for API clients or future frontend use.
    """
    raw_data = fetch_technical_news()
    new_count = 0

    for item in raw_data:
        item['impact_score'] = calculate_impact_score(item['title'], item['published'])
        if not collection.find_one({"link": item["link"]}):
            collection.insert_one(item)
            new_count += 1

    ingest_articles_to_chroma()

    return jsonify({"status": "success", "new_articles": new_count})


@app.route('/api/ask', methods=['POST'])
def ask_ai():
    data = request.json
    user_query = data.get("query")

    if not user_query:
        return jsonify({"answer": "Please ask a question!"})

    # Re-initialize on every request so it always reflects latest ChromaDB state
    vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

    doc_count = vector_db._collection.count()
    if doc_count == 0:
        return jsonify({
            "answer": (
                "The knowledge base is empty. "
                "Please hit /sync-news first to scrape and embed articles."
            )
        })

    llm = ChatOllama(model="mistral:latest", temperature=0)

    system_prompt = (
        "You are a technical news analyst for software engineers. "
        "Use ONLY the provided news context to answer the user's question. "
        "Always mention the source and published date when referencing an article. "
        "If the context does not contain relevant information, say: "
        "'I don't have updates on that specific topic in the current news feed.' "
        "Do NOT make up information.\n\n"
        "CONTEXT:\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vector_db.as_retriever(search_kwargs={"k": 6})
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    response = rag_chain.invoke({"input": user_query})
    return jsonify({"answer": response["answer"]})


if __name__ == "__main__":
    app.run(debug=True)
import os
from flask import Flask, jsonify, render_template,request
from pymongo import MongoClient
from dotenv import load_dotenv
from engine.scraper import fetch_technical_news
from engine.models import calculate_impact_score
from langchain_ollama import ChatOllama
from langchain_classic.chains import RetrievalQA
from langchain_ollama import ChatOllama

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from langchain_core.prompts import ChatPromptTemplate


# Load variables from .env file
load_dotenv()

app = Flask(__name__)

# Connect to MongoDB Atlas
# Make sure MONGO_URI is in your .env file!
client = MongoClient(os.getenv("MONGO_URI"))
db = client.insight_stream
collection = db.news_articles

@app.route('/')
def home():
    # return "InsightStream Backend is Running!"
    return render_template('index.html')

@app.route('/sync-news')
def sync_news():
    """Trigger the scraper and save unique news to MongoDB"""
    raw_data = fetch_technical_news()
    new_entries = 0
    
    for item in raw_data:
        # Avoid duplicates by checking the link
        if not collection.find_one({"link": item["link"]}):
            collection.insert_one(item)
            new_entries += 1
            
    return jsonify({
        "status": "success",
        "total_scraped": len(raw_data),
        "new_added": new_entries
    })
    


@app.route('/api/news')
def get_news():
    """
    Fetch all news from MongoDB, rank them by Impact Score,
    and return them as a sorted JSON list.
    """
    # 1. Fetch from MongoDB (Exclude the '_id' field because JSON can't read it easily)
    articles = list(collection.find({}, {"_id": 0}))
    
    # 2. Enrich with Impact Scores
    for article in articles:
        # We pass the title and date to our model's logic
        article['impact_score'] = calculate_impact_score(
            article['title'], 
            article['published']
        )
    
    # 3. Sort by Score (Highest first)
    # This uses a lambda function: "Sort this list based on the 'impact_score' key"
    sorted_news = sorted(articles, key=lambda x: x['impact_score'], reverse=True)
    
    return jsonify(sorted_news)

# @app.route('/api/ask', methods=['POST'])
# def ask_ai():
#     from flask import request
#     data = request.json
#     user_query = data.get("query")

#     # 1. Setup the Local LLM (Ollama)
#     # Ensure you have run 'ollama run llama3' in your terminal once before this
#     llm = ChatOllama(model="mistral:latest", temperature=0)

#     # 2. Use our existing ChromaDB as the 'Retriever'
#     # This searches the news we scraped for the top 3 relevant pieces
#     retriever = vector_db.as_retriever(search_kwargs={"k": 3})

#     # 3. Create the RAG Chain
#     # The 'stuff' chain puts the news snippets directly into the prompt
#     qa_chain = RetrievalQA.from_chain_type(
#         llm=llm,
#         chain_type="stuff",
#         retriever=retriever
#     )

#     # 4. Ask the question based on the news
#     # We add a small instruction to the query to ensure it uses the news
#     prompt = f"Based on the following tech news, answer this: {user_query}"
#     response = qa_chain.invoke(prompt)
    
#     return jsonify({"answer": response["result"]})

# @app.route('/api/ask', methods=['POST'])
# def ask_ai():
#     data = request.json
#     user_query = data.get("query")

#     # 1. Initialize our Local Mistral Model
#     llm = ChatOllama(model="mistral:latest", temperature=0)

#     # 2. Define the 'System Prompt'
#     # This is the "brain" instruction that tells the AI how to use the news.
#     system_prompt = (
#         "You are an expert technical news analyst. "
#         "Use the following pieces of retrieved technical news context to answer the user's question. "
#         "If the answer isn't in the context, say that you don't know based on the current feed. "
#         "Keep your answer concise and professional."
#         "\n\n"
#         "{context}"
#     )

#     prompt = ChatPromptTemplate.from_messages([
#         ("system", system_prompt),
#         ("human", "{input}"),
#     ])

#     # 3. Create the 'Stuff' Chain
#     # This part handles how the documents are formatted into the prompt.
#     question_answer_chain = create_stuff_documents_chain(llm, prompt)

#     # 4. Create the final Retrieval Chain
#     # We use our existing 'vector_db' from ChromaDB as the retriever.
#     retriever = vector_db.as_retriever(search_kwargs={"k": 3})
#     rag_chain = create_retrieval_chain(retriever, question_answer_chain)

#     # 5. Invoke the chain
#     # Note the change: we use 'input' instead of 'query' to match the prompt template
#     response = rag_chain.invoke({"input": user_query})
    
#     return jsonify({"answer": response["answer"]})

if __name__ == "__main__":
    app.run(debug=True)
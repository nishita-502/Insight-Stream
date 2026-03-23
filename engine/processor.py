from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import os

# 1. THE MODEL
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. THE MEMORY
CHROMA_PATH = os.path.join(os.getcwd(), "chroma_db")
vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

# 3. THE LOGIC
def is_duplicate(new_title):
    results = vector_db.similarity_search_with_score(new_title, k=1)
    if not results: return False
    return results[0][1] < 0.38

#If you set it to 0.2, your filter is too "weak." You will see the same news repeated by 5 different websites because their wording is slightly different.

# If you set it to 0.6, your filter is too "aggressive." It might think "Microsoft buys GitHub" and "Microsoft buys Activision" are the same thing just because they both start with "Microsoft buys."

# 0.38 is the balanced "goldilocks" number for technical news headlines. It’s tight enough to catch duplicates but loose enough to let distinct stories through.
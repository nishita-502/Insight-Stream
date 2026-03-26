# from datetime import datetime

# # 1. THE WEIGHTS (How much we value certain topics)
# # These are high-priority terms in the current tech market.
# HOT_KEYWORDS = {
#     "AI": 2.0,
#     "LLM": 2.5,
#     "Nvidia": 2.0,
#     "Open Source": 1.5,
#     "Microsoft": 1.0,
#     "Azure": 1.0,
#     "Cybersecurity": 1.8
# }

# def calculate_impact_score(title, published_date):
#     """
#     Returns a score from 1 to 10.
#     10 = Breaking, high-impact news.
#     1 = Older, generic tech news.
#     """
#     score = 4.0  # The "Base Score"
    
#     # A. KEYWORD BOOST
#     # We check if the title contains our 'Hot' words.
#     for word, boost in HOT_KEYWORDS.items():
#         if word.lower() in title.lower():
#             score += boost
            
#     # B. FRESHNESS DECAY (The 'Time' Factor)
#     # News loses value as it gets older.
#     try:
#         # Convert the string date from RSS to a Python object
#         # Note: We use a simplified try/except for different RSS date formats
#         pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
#         hours_old = (datetime.utcnow() - pub_date.total_seconds()) / 3600
        
#         # We subtract 0.2 points for every hour that has passed.
#         score -= (hours_old * 0.2)
#     except:
#         pass # If date is missing/bad, we just stick to keyword score

#     # C. BOUNDARIES
#     # We ensure the score stays within a logical range (1.0 to 10.0)
#     return round(max(min(score, 10.0), 1.0), 1)


from datetime import datetime

# 1. THE WEIGHTS (How much we value certain topics)
HOT_KEYWORDS = {
    "AI": 2.0,
    "LLM": 2.5,
    "Nvidia": 2.0,
    "Open Source": 1.5,
    "Microsoft": 1.0,
    "Azure": 1.0,
    "Cybersecurity": 1.8
}

def calculate_impact_score(title, published_date):
    """
    Returns a score from 1 to 10.
    10 = Breaking, high-impact news.
    1 = Older, generic tech news.
    """
    score = 4.0  # Base Score

    # A. KEYWORD BOOST
    for word, boost in HOT_KEYWORDS.items():
        if word.lower() in title.lower():
            score += boost

    # B. FRESHNESS DECAY
    try:
        pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        
        # ✅ FIX: subtract two datetimes → timedelta → then call .total_seconds()
        # Previously was: (datetime.utcnow() - pub_date.total_seconds()) which is wrong
        hours_old = (datetime.utcnow() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
        score -= (hours_old * 0.2)
    except Exception as e:
        print(f"[models] Date parsing error: {e}")  # No longer silent!

    # C. BOUNDARIES
    return round(max(min(score, 10.0), 1.0), 1)
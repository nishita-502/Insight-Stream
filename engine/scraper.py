import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Sources to track (You can add more later)
FEEDS = {
    "GitHub": "https://github.blog/feed/",
    "AWS": "https://aws.amazon.com/blogs/aws/feed/",
    "Microsoft": "https://devblogs.microsoft.com/dotnet/feed/",
    "TechCrunch": "https://techcrunch.com/category/artificial-intelligence/feed/"
}

def fetch_technical_news():
    news_items = []
    
    for source, url in FEEDS.items():
        try:
            print(f"Scraping {source}...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:5]: # Get top 5 latest
                # Clean the summary (remove HTML tags)
                summary_html = entry.summary if 'summary' in entry else ""
                clean_summary = BeautifulSoup(summary_html, "html.parser").get_text()
                
                item = {
                    "title": entry.title,
                    "link": entry.link,
                    "summary": clean_summary[:250] + "...", # Keep it concise
                    "source": source,
                    "published": entry.published if 'published' in entry else datetime.utcnow().isoformat(),
                    "category": "Tech"
                }
                news_items.append(item)
        except Exception as e:
            print(f"Error scraping {source}: {e}")
            
    return news_items
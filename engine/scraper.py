import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

FEEDS = {
    "GitHub": "https://github.blog/feed/",
    "AWS": "https://aws.amazon.com/blogs/aws/feed/",
    "Microsoft": "https://devblogs.microsoft.com/dotnet/feed/",
    "TechCrunch": "https://techcrunch.com/category/artificial-intelligence/feed/"
}

def fetch_technical_news():
    news_items = []
    # Set the cutoff to 7 days ago
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    for source, url in FEEDS.items():
        try:
            print(f"Scraping {source}...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                # 1. DATE PARSING LOGIC
                # RSS feeds use a 'published_parsed' tuple. We convert it to a datetime object.
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                else:
                    pub_date = datetime.utcnow()

                # 2. THE 7-DAY FILTER
                # If the article is older than our cutoff, we skip it entirely.
                if pub_date < seven_days_ago:
                    continue 

                # Clean the summary
                summary_html = entry.summary if 'summary' in entry else ""
                clean_summary = BeautifulSoup(summary_html, "html.parser").get_text()
                
                item = {
                    "title": entry.title,
                    "link": entry.link,
                    "summary": clean_summary[:250].strip() + "...", 
                    "source": source,
                    "published": pub_date.isoformat(), # Use the actual parsed date
                    "category": "Tech"
                }
                news_items.append(item)
                
                # Limit to top 10 fresh items per source to keep it fast
                if len([i for i in news_items if i['source'] == source]) >= 10:
                    break

        except Exception as e:
            print(f"Error scraping {source}: {e}")
            
    return news_items
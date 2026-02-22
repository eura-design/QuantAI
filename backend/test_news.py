import os
import sys
from analyzer import fetch_crypto_news
from dotenv import load_dotenv

load_dotenv()

def test_news():
    print("Testing News (EN)...")
    en_news = fetch_crypto_news('en')
    print(f"EN News: {en_news}")
    
    print("\nTesting News (KO)...")
    ko_news = fetch_crypto_news('ko')
    print(f"KO News: {ko_news}")

if __name__ == "__main__":
    test_news()

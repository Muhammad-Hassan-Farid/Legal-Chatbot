#!/usr/bin/env python3
"""
Test the QanoonMate scraping function
"""
import sys
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
sys.path.insert(0, '/Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot')
django.setup()

from chat.views import scrape_qanoonmate_response

# Test queries
test_queries = [
    "What is the right to life?",
    "What are fundamental rights?",
]

print("=" * 70)
print("Testing QanoonMate Web Scraping Function")
print("=" * 70)

for query in test_queries:
    print(f"\n📝 Testing query: {query}")
    print("-" * 70)
    
    try:
        response = scrape_qanoonmate_response(query)
        
        if "Error" in response or "error" in response:
            print(f"❌ Error: {response[:200]}")
        else:
            print(f"✓ Response received ({len(response)} chars)")
            print(f"Preview: {response[:300]}...")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)[:200]}")

print("\n" + "=" * 70)
print("Test completed!")
print("=" * 70)

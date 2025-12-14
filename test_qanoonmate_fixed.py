#!/usr/bin/env python3
"""
Test script to verify QanoonMate scraping fix
"""
import sys
import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
sys.path.insert(0, '/Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot')
django.setup()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from chat.views import scrape_qanoonmate_response

# Test queries
test_queries = [
    "What are fundamental rights in Pakistan?",
    "What is the right to life?",
]

print("=" * 80)
print("Testing QanoonMate Web Scraping with Improved Implementation")
print("=" * 80)

for i, query in enumerate(test_queries, 1):
    print(f"\n📝 Test {i}: {query}")
    print("-" * 80)
    
    try:
        response = scrape_qanoonmate_response(query)
        
        if "Error" in response or "error" in response or "did not provide" in response.lower():
            print(f"⚠️  Response may be incomplete/error:")
            print(f"    {response[:200]}...")
        else:
            response_preview = response[:200].replace('\n', ' ')
            print(f"✅ Success! Response received ({len(response)} chars)")
            print(f"   Preview: {response_preview}...")
            print(f"\n   Full Response:")
            print("   " + "\n   ".join(response.split('\n')[:10]))
    
    except Exception as e:
        print(f"❌ Exception: {str(e)[:200]}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)

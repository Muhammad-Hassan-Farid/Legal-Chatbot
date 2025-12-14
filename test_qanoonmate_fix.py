#!/usr/bin/env python
"""
Test script to verify QanoonMate scraper fix
Tests if the Chat mode selection works properly
Run: python test_qanoonmate_fix.py
"""

import os
import sys
import django
import json
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
sys.path.insert(0, '/Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot')
django.setup()

from chat.views import scrape_qanoonmate_response
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_qanoonmate_scraper():
    """Test the updated QanoonMate scraper"""
    
    test_queries = [
        "What are fundamental rights in Pakistan?",
        "Explain Article 4 of the Constitution",
        "What is the right to life in Pakistan?"
    ]
    
    logger.info("=" * 80)
    logger.info("QANOONMATE SCRAPER FIX TEST")
    logger.info("=" * 80)
    logger.info("Testing with Chat mode selection fix...")
    logger.info("")
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST {i}: {query}")
        logger.info(f"{'='*80}")
        
        try:
            response = scrape_qanoonmate_response(query)
            
            # Check if response is valid
            if not response:
                logger.error(f"❌ FAILED: Empty response")
                continue
            
            # Check if response contains "Drafting" (the bug)
            if "Drafting" in response or "Draft legal documents" in response:
                logger.error(f"❌ FAILED: Still getting Drafting mode response")
                logger.error(f"Response preview: {response[:200]}")
                continue
            
            # Check if response is substantial
            if len(response) < 100:
                logger.warning(f"⚠️  Response is short ({len(response)} chars)")
                logger.warning(f"Response: {response}")
                continue
            
            logger.info(f"✅ SUCCESS: Got proper response")
            logger.info(f"Response length: {len(response)} characters")
            logger.info(f"Response preview:\n{response[:300]}...")
            
        except Exception as e:
            logger.error(f"❌ EXCEPTION: {str(e)}")
            continue
        
        # Add delay between tests
        if i < len(test_queries):
            logger.info(f"\nWaiting 3 seconds before next test...")
            time.sleep(3)
    
    logger.info(f"\n{'='*80}")
    logger.info("TEST COMPLETE")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    test_qanoonmate_scraper()

#!/usr/bin/env python
"""Quick test for QanoonMate response extraction fix."""

import os
import sys
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
django.setup()

from chat.views import scrape_qanoonmate_response

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qanoonmate():
    """Test QanoonMate response with improved extraction logic."""
    query = "What are fundamental rights in Pakistan?"
    
    logger.info(f"Testing QanoonMate with query: {query}")
    logger.info("=" * 70)
    
    response = scrape_qanoonmate_response(query)
    
    logger.info("=" * 70)
    logger.info(f"Response length: {len(response)} characters")
    logger.info(f"Response preview:\n{response[:500]}\n...")
    
    # Check if response is valid
    if not response:
        logger.error("❌ No response returned")
        return False
    
    if "Drafting Draft legal documents" in response:
        logger.error("❌ FAILED: Still returning 'Drafting' button text!")
        return False
    
    if len(response) < 150:
        logger.warning(f"⚠️  Response seems short: {len(response)} chars")
        return False
    
    # Check for legal content keywords
    legal_keywords = ["rights", "pakistan", "constitution", "law", "legal", "article"]
    has_legal_content = any(keyword in response.lower() for keyword in legal_keywords)
    
    if not has_legal_content:
        logger.error(f"❌ Response doesn't seem to contain legal content")
        return False
    
    logger.info("✅ QanoonMate test PASSED - proper legal response returned")
    return True

if __name__ == '__main__':
    try:
        success = test_qanoonmate()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test error: {str(e)}", exc_info=True)
        sys.exit(1)

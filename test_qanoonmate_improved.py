#!/usr/bin/env python3
"""
Validate the improved QanoonMate scraper function
Tests: JavaScript submission, improved extraction, response quality
"""

import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
django.setup()

from chat.views import scrape_qanoonmate_response
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_qanoonmate_improved():
    """Test the improved QanoonMate scraper"""
    
    logger.info("="*70)
    logger.info("TESTING IMPROVED QANOONMATE SCRAPER")
    logger.info("="*70)
    
    test_queries = [
        "What are fundamental rights in Pakistan?",
        "Explain Article 25 of the Constitution",
    ]
    
    for query in test_queries:
        logger.info(f"\n{'='*70}")
        logger.info(f"Query: {query}")
        logger.info("="*70)
        
        try:
            response = scrape_qanoonmate_response(query)
            
            logger.info(f"\n✓ Response received: {len(response)} characters")
            
            # Validation checks
            checks = {
                "Has content": len(response) > 200,
                "No 'Drafting' text": "Drafting" not in response,
                "No 'Draft legal' text": "Draft legal" not in response,
                "No 'AI is typing'": "AI is typing" not in response,
                "Contains legal content": any(x in response for x in ["Article", "right", "Constitution", "Pakistan"]),
                "Not an error message": not response.startswith("Error") and not response.startswith("QanoonMate did not"),
            }
            
            logger.info("\nValidation checks:")
            all_passed = True
            for check_name, result in checks.items():
                status = "✓" if result else "✗"
                logger.info(f"  {status} {check_name}")
                if not result:
                    all_passed = False
            
            if all_passed:
                logger.info("\n✓✓✓ ALL CHECKS PASSED ✓✓✓")
            else:
                logger.warning("\n⚠ Some checks failed")
            
            # Show preview
            logger.info(f"\nResponse preview (first 300 chars):")
            logger.info(response[:300])
            logger.info("\n...")
            logger.info("\nResponse preview (last 200 chars):")
            logger.info(response[-200:])
            
        except Exception as e:
            logger.error(f"✗ Error: {str(e)}", exc_info=True)
        
        # Wait between requests
        logger.info("\nWaiting 5 seconds before next query...")
        time.sleep(5)
    
    logger.info("\n" + "="*70)
    logger.info("TEST COMPLETE")
    logger.info("="*70)

if __name__ == "__main__":
    test_qanoonmate_improved()

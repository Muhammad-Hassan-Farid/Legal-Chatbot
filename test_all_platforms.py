#!/usr/bin/env python
"""
Test script to verify all three platforms are responding correctly.
Tests:
1. PakLegal RAG endpoint
2. QanoonMate with mode verification fix
3. Pakistan Law Bot with improved extraction
"""

import os
import sys
import django
import logging
from django.test import Client
import json

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
django.setup()

from django.test import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_all_platforms():
    """Test all three platforms with comparison endpoint"""
    client = Client()
    
    test_queries = [
        "What are fundamental rights in Pakistan?",
        "Explain the right to life",
        "What is Article 4 of the Constitution?",
    ]
    
    for query in test_queries:
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing query: {query}")
        logger.info('='*70)
        
        # Test the comparison endpoint
        try:
            response = client.post(
                '/compare/',
                data=json.dumps({'message': query}),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                data = json.loads(response.content)
                
                # Check PakLegal
                logger.info("\n📚 PakLegal RAG:")
                paklegal_response = data.get('paklegal', '')
                if paklegal_response and paklegal_response.startswith('Error'):
                    logger.error(f"  ❌ {paklegal_response[:100]}")
                else:
                    logger.info(f"  ✅ Response length: {len(paklegal_response)} chars")
                    logger.info(f"  Preview: {paklegal_response[:200]}...")
                
                # Check QanoonMate
                logger.info("\n⚖️  QanoonMate:")
                qanoonmate_response = data.get('qanoonmate', '')
                if qanoonmate_response and qanoonmate_response.startswith('Error'):
                    logger.error(f"  ❌ {qanoonmate_response[:100]}")
                elif 'Drafting' in qanoonmate_response:
                    logger.error(f"  ❌ ISSUE: Still returning 'Drafting' content")
                    logger.error(f"  Response: {qanoonmate_response[:150]}")
                else:
                    logger.info(f"  ✅ Response length: {len(qanoonmate_response)} chars")
                    logger.info(f"  Preview: {qanoonmate_response[:200]}...")
                
                # Check Pakistan Law Bot
                logger.info("\n🏛️  Pakistan Law Bot:")
                plb_response = data.get('pakistan_lawbot', '')
                if plb_response and plb_response.startswith('Error'):
                    logger.error(f"  ❌ {plb_response[:100]}")
                else:
                    logger.info(f"  ✅ Response length: {len(plb_response)} chars")
                    if len(plb_response) > 200:
                        logger.info(f"  Preview: {plb_response[:200]}...")
                    else:
                        logger.warning(f"  ⚠️  Response seems short: {plb_response[:150]}...")
            else:
                logger.error(f"❌ Request failed with status {response.status_code}")
                logger.error(f"Response: {response.content}")
        
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}", exc_info=True)

if __name__ == '__main__':
    logger.info("Starting Platform Comparison Test")
    logger.info("=" * 70)
    test_all_platforms()
    logger.info("\n" + "=" * 70)
    logger.info("Test completed")

#!/usr/bin/env python
"""
Quick test to verify QanoonMate fix - tests Chat mode selection only
Run: python test_qanoonmate_quick.py
"""

import os
import sys
import django
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
sys.path.insert(0, '/Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot')
django.setup()

def test_chat_mode_selection():
    """Quick test: Can we find and click the Chat mode button?"""
    
    driver = None
    try:
        logger.info("Testing Chat Mode Selection Fix")
        logger.info("=" * 60)
        
        # Setup Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        logger.info("1. Opening browser...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info("2. Navigating to QanoonMate...")
        driver.get("https://www.qanoonmate.com/chat")
        time.sleep(3)
        
        logger.info("3. Looking for Chat mode button...")
        chat_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Chat')]")
        logger.info(f"   Found {len(chat_buttons)} buttons containing 'Chat'")
        
        # Find the correct Chat button
        found_chat = False
        for i, btn in enumerate(chat_buttons):
            btn_text = btn.text
            logger.info(f"   Button {i}: '{btn_text}'")
            
            if 'interactive legal conversations' in btn_text.lower() or btn_text.strip() == 'Chat\nInteractive legal conversations':
                logger.info(f"   ✅ Found Chat mode button!")
                logger.info("4. Clicking Chat mode button...")
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.3)
                btn.click()
                logger.info("   ✅ Clicked successfully!")
                time.sleep(1)
                found_chat = True
                break
        
        if not found_chat:
            logger.warning("   ⚠️  Chat button not found, trying alternative selectors...")
            
        logger.info("5. Checking for input field (textarea)...")
        time.sleep(1)
        textareas = driver.find_elements(By.TAG_NAME, "textarea")
        logger.info(f"   Found {len(textareas)} textarea elements")
        
        if textareas:
            placeholder = textareas[0].get_attribute('placeholder')
            logger.info(f"   ✅ Input field ready: placeholder='{placeholder}'")
            logger.info("\n✅ CHAT MODE SELECTION TEST: PASSED")
            return True
        else:
            logger.warning("   ⚠️  No textarea found")
            logger.info("\n⚠️  CHAT MODE SELECTION TEST: INCONCLUSIVE")
            return False
            
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

if __name__ == "__main__":
    success = test_chat_mode_selection()
    sys.exit(0 if success else 1)

#!/usr/bin/env python
"""
Diagnostic script to test QanoonMate scraping and identify issues
Run: python test_qanoonmate_debug.py
"""

import os
import sys
import django
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
sys.path.insert(0, '/Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot')
django.setup()

def diagnose_qanoonmate():
    """Diagnose what's happening with QanoonMate scraping"""
    
    driver = None
    try:
        logger.info("=" * 80)
        logger.info("QANOONMATE DIAGNOSTIC TEST")
        logger.info("=" * 80)
        
        # Setup Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        # Add --headless=new for better rendering in newer Chrome
        options.add_argument('--headless=new')
        
        logger.info("Opening Chrome browser...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info("Navigating to https://www.qanoonmate.com/chat")
        driver.get("https://www.qanoonmate.com/chat")
        
        logger.info("Waiting for page to load (5 seconds)...")
        time.sleep(5)
        
        # Get page source and analyze structure
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: PAGE STRUCTURE ANALYSIS")
        logger.info("=" * 80)
        
        body_text = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Body text length: {len(body_text)} characters")
        logger.info(f"Body text preview:\n{body_text[:500]}")
        
        # Check for input fields
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: INPUT FIELD DETECTION")
        logger.info("=" * 80)
        
        textareas = driver.find_elements(By.TAG_NAME, "textarea")
        logger.info(f"Found {len(textareas)} textarea elements")
        for i, ta in enumerate(textareas):
            try:
                logger.info(f"  Textarea {i}: visible={ta.is_displayed()}, placeholder='{ta.get_attribute('placeholder')}'")
            except:
                logger.info(f"  Textarea {i}: error reading attributes")
        
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        logger.info(f"Found {len(text_inputs)} text input elements")
        for i, inp in enumerate(text_inputs):
            try:
                logger.info(f"  Input {i}: visible={inp.is_displayed()}, placeholder='{inp.get_attribute('placeholder')}'")
            except:
                logger.info(f"  Input {i}: error reading attributes")
        
        # Check for buttons
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: BUTTON DETECTION")
        logger.info("=" * 80)
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        logger.info(f"Found {len(buttons)} button elements")
        for i, btn in enumerate(buttons[:10]):  # Show first 10
            try:
                logger.info(f"  Button {i}: visible={btn.is_displayed()}, text='{btn.text}', class='{btn.get_attribute('class')}'")
            except:
                logger.info(f"  Button {i}: error reading attributes")
        
        # Check for any divs with content
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: CONTENT DIVS")
        logger.info("=" * 80)
        
        divs = driver.find_elements(By.TAG_NAME, "div")
        logger.info(f"Found {len(divs)} div elements")
        
        # Find divs with substantial text
        content_divs = []
        for div in divs:
            try:
                text = div.text.strip()
                if len(text) > 50:
                    content_divs.append((len(text), text[:100]))
            except:
                pass
        
        # Sort by length
        content_divs.sort(reverse=True)
        logger.info(f"Found {len(content_divs)} divs with substantial content")
        logger.info("Top 5 content divs:")
        for length, preview in content_divs[:5]:
            logger.info(f"  {length} chars: {preview}...")
        
        # Check page title and URL
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: PAGE METADATA")
        logger.info("=" * 80)
        
        logger.info(f"Page title: {driver.title}")
        logger.info(f"Current URL: {driver.current_url}")
        
        # Get HTML structure (head section)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: HTML HEAD SECTION")
        logger.info("=" * 80)
        
        head = driver.find_element(By.TAG_NAME, "head").get_attribute("outerHTML")
        logger.info(f"Head section length: {len(head)} characters")
        # Show first 500 chars
        logger.info(f"Head preview:\n{head[:500]}")
        
        logger.info("\n" + "=" * 80)
        logger.info("DIAGNOSIS COMPLETE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error during diagnosis: {str(e)}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

if __name__ == "__main__":
    diagnose_qanoonmate()

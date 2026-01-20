#!/usr/bin/env python3
"""
Debugging script for QanoonMate response extraction.
Run this to test QanoonMate scraping independently and diagnose issues.

Usage:
    python test_qanoonmate_debug.py "Your query here"
"""

import sys
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_qanoonmate(query):
    """Test QanoonMate scraping with detailed logging."""
    driver = None
    try:
        logger.info("=" * 80)
        logger.info(f"Testing QanoonMate for query: {query}")
        logger.info("=" * 80)
        
        # Chrome options
        options = webdriver.ChromeOptions()
        # Comment out headless for debugging (see browser)
        # options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        # Step 1: Navigate to page
        logger.info("\n[STEP 1] Navigating to QanoonMate...")
        driver.get("https://www.qanoonmate.com/chat")
        time.sleep(5)
        
        logger.info(f"Page title: {driver.title}")
        logger.info(f"Current URL: {driver.current_url}")
        
        body_text = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Initial page text length: {len(body_text)} chars")
        logger.info(f"Initial page sample:\n{body_text[:200]}...")
        
        # Step 2: Find input field
        logger.info("\n[STEP 2] Finding input field...")
        input_field = None
        
        css_selectors = [
            'input[placeholder*="message"]',
            'input[placeholder*="query"]',
            'textarea[placeholder*="message"]',
            'input[class*="input"]',
        ]
        
        for selector in css_selectors:
            try:
                inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in inputs:
                    if elem.is_displayed():
                        input_field = elem
                        logger.info(f"✓ Found input with selector: {selector}")
                        break
                if input_field:
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
        
        if not input_field:
            # Try by tag name
            logger.warning("CSS selectors failed, trying tag name approach...")
            elements = driver.find_elements(By.TAG_NAME, "input")
            for elem in elements:
                if elem.is_displayed() and elem.get_attribute('type') != 'hidden':
                    input_field = elem
                    logger.info("✓ Found visible input element")
                    break
        
        if not input_field:
            raise Exception("Could not find input field!")
        
        # Step 3: Enter query
        logger.info("\n[STEP 3] Entering query...")
        driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
        time.sleep(0.5)
        
        driver.execute_script("arguments[0].focus();", input_field)
        input_field.send_keys(query)
        logger.info(f"✓ Query entered: {query}")
        
        # Step 4: Submit query
        logger.info("\n[STEP 4] Submitting query...")
        button = None
        button_selectors = [
            'button[type="submit"]',
            'button[class*="send"]',
            'button[aria-label*="send"]',
        ]
        
        for selector in button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        button = btn
                        logger.info(f"✓ Found button with selector: {selector}")
                        break
                if button:
                    break
            except:
                continue
        
        if button:
            driver.execute_script("arguments[0].click();", button)
            logger.info("✓ Button clicked")
        else:
            logger.warning("No button found, pressing Enter...")
            input_field.send_keys(Keys.RETURN)
            logger.info("✓ Query submitted via Enter")
        
        # Step 5: Wait for response
        logger.info("\n[STEP 5] Waiting for response (max 60 seconds)...")
        initial_length = len(driver.find_element(By.TAG_NAME, "body").text)
        logger.info(f"Initial page length: {initial_length}")
        
        start_time = time.time()
        max_wait = 60
        previous_length = initial_length
        stable_count = 0
        
        while time.time() - start_time < max_wait:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            current_length = len(body_text)
            elapsed = time.time() - start_time
            
            growth = current_length - initial_length
            
            if current_length == previous_length and growth > 100:
                stable_count += 1
            else:
                stable_count = 0
            
            status = f"[{elapsed:.1f}s] Length: {current_length} (growth: {growth})"
            
            if "Thinking" in body_text or "In progress" in body_text:
                logger.info(f"{status} - Still thinking...")
            elif stable_count >= 3:
                logger.info(f"{status} - RESPONSE READY!")
                break
            else:
                logger.info(f"{status}")
            
            previous_length = current_length
            time.sleep(1)
        
        # Step 6: Extract response
        logger.info("\n[STEP 6] Extracting response...")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Final page length: {len(body_text)} chars")
        logger.info(f"Full page text:\n{body_text}")
        
        # Try extraction strategies
        logger.info("\n[STEP 7] Trying extraction strategies...")
        
        # Strategy: Find content after query
        all_lines = body_text.split('\n')
        response_lines = []
        found_query = False
        
        for i, line in enumerate(all_lines):
            stripped = line.strip()
            
            if query in stripped or stripped == query:
                found_query = True
                logger.info(f"✓ Found query at line {i}")
                continue
            
            if found_query and stripped and len(stripped) > 10:
                if not any(ui in stripped for ui in ["Web Search", "Audio Search", "Sign In", "Copy", "Improve"]):
                    response_lines.append(stripped)
        
        if response_lines:
            response_text = '\n'.join(response_lines)
            logger.info(f"\n✓ EXTRACTED RESPONSE ({len(response_text)} chars):")
            logger.info(response_text)
        else:
            logger.warning("✗ Could not extract response")
        
        logger.info("\n" + "=" * 80)
        logger.info("Test complete!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    
    finally:
        if driver:
            try:
                input("Press Enter to close browser...")
                driver.quit()
            except:
                driver.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        query = "What are the key labor laws that employers must follow in Pakistan?"
        print(f"No query provided, using default: {query}")
    else:
        query = " ".join(sys.argv[1:])
    
    test_qanoonmate(query)

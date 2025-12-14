#!/usr/bin/env python3
"""
Quick QanoonMate debug - check if responses load in DOM or via API
"""

import os
import sys
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qanoonmate_simple():
    """Simple test - check if response appears in DOM"""
    driver = None
    try:
        logger.info("Starting QanoonMate test...")
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info("Loading QanoonMate...")
        driver.get("https://www.qanoonmate.com/chat")
        time.sleep(3)
        
        # Check initial state
        body_before = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Initial page length: {len(body_before)} chars")
        logger.info(f"Initial content: {body_before[:150]}")
        
        # Find input
        logger.info("\nFinding input field...")
        try:
            wait = WebDriverWait(driver, 10)
            input_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea")))
            logger.info("✓ Input field found")
        except:
            logger.error("✗ Could not find input field")
            return
        
        # Submit query
        query = "What are fundamental rights?"
        logger.info(f"\nSubmitting query: {query}")
        input_elem.click()
        time.sleep(0.3)
        input_elem.send_keys(query)
        
        # Find and click send button
        buttons = driver.find_elements(By.TAG_NAME, "button")
        if buttons:
            logger.info(f"Found {len(buttons)} buttons, clicking last one...")
            buttons[-1].click()
        else:
            logger.info("No button, pressing Enter...")
            input_elem.send_keys(Keys.RETURN)
        
        # Monitor response
        logger.info("\nWaiting for response (30 seconds)...")
        for i in range(30):
            time.sleep(1)
            body = driver.find_element(By.TAG_NAME, "body").text
            body_len = len(body)
            
            if body_len > len(body_before) + 200:
                logger.info(f"[{i}s] Content changed! Length: {body_len}")
                logger.info(f"     New content: {body[:250]}")
                break
            elif i % 5 == 0:
                logger.info(f"[{i}s] Waiting... Length: {body_len}")
        
        # Final check
        logger.info("\n" + "="*60)
        logger.info("FINAL RESULT")
        logger.info("="*60)
        
        body_final = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Final page length: {len(body_final)} chars")
        logger.info(f"Change from initial: {len(body_final) - len(body_before)} chars")
        
        if "Drafting" in body_final or "Draft legal" in body_final:
            logger.warning("⚠ WARNING: Page still contains 'Drafting' text (button label)")
        
        if len(body_final) > len(body_before) + 100:
            logger.info("✓ Content appears to have loaded")
            logger.info(f"\nContent preview:\n{body_final[:500]}")
        else:
            logger.error("✗ No significant content loaded")
            logger.info(f"\nFull page:\n{body_final}")
        
        # Check for specific response elements
        logger.info("\n" + "="*60)
        logger.info("DOM STRUCTURE CHECK")
        logger.info("="*60)
        
        selectors = [
            "div[class*='message']",
            "div[class*='response']", 
            "div[class*='chat']",
            "div[class*='content']",
            "[role='article']",
            "[role='presentation']"
        ]
        
        for sel in selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    logger.info(f"✓ {sel}: {len(elems)} elements")
            except:
                pass
        
        # Check JavaScript execution capability
        logger.info("\n" + "="*60)
        logger.info("JAVASCRIPT EXECUTION CHECK")
        logger.info("="*60)
        
        try:
            result = driver.execute_script("return document.body.textContent.length")
            logger.info(f"✓ JavaScript works - body textContent length: {result}")
        except Exception as e:
            logger.error(f"✗ JavaScript error: {e}")
        
        # Check page source for API calls
        logger.info("\n" + "="*60)
        logger.info("SOURCE CODE CHECK")
        logger.info("="*60)
        
        source = driver.page_source
        if 'api' in source.lower():
            logger.info("✓ Page contains 'api' references")
        if 'fetch' in source:
            logger.info("✓ Page uses fetch()")
        if 'XMLHttpRequest' in source:
            logger.info("✓ Page uses XMLHttpRequest")
        if 'WebSocket' in source:
            logger.info("✓ Page uses WebSocket")
        
        logger.info(f"✓ Total page source: {len(source)} chars")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    
    finally:
        if driver:
            driver.quit()
            logger.info("\n✓ Browser closed")

if __name__ == "__main__":
    test_qanoonmate_simple()

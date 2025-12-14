#!/usr/bin/env python3
"""
Debug QanoonMate form submission - test different methods
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qanoonmate_submission_methods():
    """Test different form submission methods"""
    driver = None
    try:
        logger.info("Testing QanoonMate form submission methods...")
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info("Loading QanoonMate...")
        driver.get("https://www.qanoonmate.com/chat")
        time.sleep(3)
        
        # Inspect page structure
        logger.info("\n" + "="*70)
        logger.info("INSPECTING PAGE STRUCTURE")
        logger.info("="*70)
        
        # Check for form
        forms = driver.find_elements(By.TAG_NAME, "form")
        logger.info(f"Forms found: {len(forms)}")
        for i, form in enumerate(forms):
            logger.info(f"  Form {i}: action='{form.get_attribute('action')}', method='{form.get_attribute('method')}'")
        
        # Check for buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        logger.info(f"Buttons found: {len(buttons)}")
        for i, btn in enumerate(buttons[-5:]):  # Last 5 buttons
            logger.info(f"  Button {len(buttons)-5+i}: text='{btn.text[:50]}', type='{btn.get_attribute('type')}'")
        
        # Get textarea
        textareas = driver.find_elements(By.CSS_SELECTOR, "textarea")
        logger.info(f"Textareas found: {len(textareas)}")
        
        if not textareas:
            logger.error("No textarea found - can't test submission")
            return
        
        textarea = textareas[0]
        logger.info(f"Textarea name: '{textarea.get_attribute('name')}'")
        logger.info(f"Textarea placeholder: '{textarea.get_attribute('placeholder')}'")
        
        # Get initial page size
        initial_body = driver.find_element(By.TAG_NAME, "body").text
        initial_len = len(initial_body)
        logger.info(f"\nInitial page size: {initial_len} chars")
        
        # Test submission methods
        logger.info("\n" + "="*70)
        logger.info("TEST 1: ENTER KEY SUBMISSION")
        logger.info("="*70)
        
        query = "What are fundamental rights?"
        textarea.click()
        time.sleep(0.5)
        textarea.send_keys(query)
        logger.info(f"Typed query: {query}")
        
        time.sleep(0.5)
        logger.info("Pressing Enter...")
        textarea.send_keys(Keys.RETURN)
        
        logger.info("Waiting 15 seconds for response...")
        for i in range(15):
            time.sleep(1)
            body = driver.find_element(By.TAG_NAME, "body").text
            body_len = len(body)
            if body_len > initial_len + 100:
                logger.info(f"  [{i+1}s] Content changed! New size: {body_len} (+{body_len - initial_len})")
                break
            elif (i+1) % 5 == 0:
                logger.info(f"  [{i+1}s] Still waiting... size: {body_len}")
        
        final_body_enter = driver.find_element(By.TAG_NAME, "body").text
        size_change_enter = len(final_body_enter) - initial_len
        logger.info(f"\nResult: {size_change_enter} chars added")
        
        if size_change_enter > 200:
            logger.info("✓ SUCCESS: Response loaded with Enter key")
        else:
            logger.warning("✗ FAILED: No response with Enter key")
        
        # Reset
        logger.info("\n" + "="*70)
        logger.info("RESETTING FOR NEXT TEST...")
        logger.info("="*70)
        driver.quit()
        
        # Test in non-headless mode to see what's happening
        logger.info("\nOpening non-headless browser for visual inspection...")
        options.add_argument('--headless')
        options.set_headless(False)  # NOT headless
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info("Loading QanoonMate (non-headless)...")
        driver.get("https://www.qanoonmate.com/chat")
        time.sleep(3)
        
        logger.info("\n" + "="*70)
        logger.info("VISUAL TEST (Keep browser open for 20 seconds)")
        logger.info("="*70)
        logger.info("The browser is now open in foreground. You can see if Enter key works.")
        logger.info("Submitting a test query...")
        
        textarea = driver.find_element(By.CSS_SELECTOR, "textarea")
        textarea.click()
        time.sleep(0.3)
        textarea.send_keys("Test query about rights")
        time.sleep(0.3)
        logger.info("Pressing Enter...")
        textarea.send_keys(Keys.RETURN)
        
        logger.info("Waiting 20 seconds - observe the browser...")
        time.sleep(20)
        
        final_body_visual = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Final page size: {len(final_body_visual)} chars")
        logger.info(f"Content preview: {final_body_visual[:200]}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")


if __name__ == "__main__":
    test_qanoonmate_submission_methods()

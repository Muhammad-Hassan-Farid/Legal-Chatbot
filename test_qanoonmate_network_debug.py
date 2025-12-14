#!/usr/bin/env python3
"""
Debug script to understand QanoonMate response loading mechanism.
Uses a non-headless browser and network monitoring to see where response comes from.
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_qanoonmate_with_network():
    """Test QanoonMate with network monitoring enabled"""
    driver = None
    try:
        logger.info("=" * 80)
        logger.info("QanoonMate Network Debug Test")
        logger.info("=" * 80)
        
        # Chrome options - NOT headless so we can see what's happening
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Enable logging
        options.add_argument('--enable-logging')
        options.add_argument('--v=1')
        
        logger.info("Opening Chrome browser (non-headless)...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        # Enable Chrome DevTools Protocol to monitor network
        logger.info("Initializing network monitoring...")
        try:
            driver.execute_cdp_cmd('Network.enable', {})
            logger.info("Network monitoring enabled via CDP")
        except:
            logger.warning("CDP network monitoring not available, will use browser logs instead")
        
        logger.info("Navigating to QanoonMate...")
        driver.get("https://www.qanoonmate.com/chat")
        
        logger.info("Waiting for page to load...")
        time.sleep(5)
        
        # Check page state
        logger.info("\n" + "=" * 80)
        logger.info("PAGE STATE BEFORE QUERY")
        logger.info("=" * 80)
        
        body_text_before = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Body text length: {len(body_text_before)} chars")
        logger.info(f"Body text preview: {body_text_before[:200]}")
        
        # Find and fill input field
        logger.info("\nFinding input field...")
        try:
            wait = WebDriverWait(driver, 10)
            input_field = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea"))
            )
            logger.info("✓ Input field found (textarea)")
        except:
            try:
                input_field = driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                logger.info("✓ Input field found (text input)")
            except:
                logger.error("Could not find input field!")
                return
        
        # Type query
        query = "What are fundamental rights in Pakistan?"
        logger.info(f"\nEntering query: {query}")
        input_field.click()
        time.sleep(0.5)
        input_field.clear()
        input_field.send_keys(query)
        logger.info("Query entered")
        
        # Find and click send button
        logger.info("\nFinding send button...")
        try:
            button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            if not button:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                button = buttons[-1] if buttons else None
        except:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            button = buttons[-1] if buttons else None
        
        if button:
            logger.info("✓ Send button found, clicking...")
            button.click()
            logger.info("Query submitted")
        else:
            logger.info("No button found, pressing Enter...")
            input_field.send_keys(Keys.RETURN)
            logger.info("Query submitted via Enter")
        
        # Wait and monitor response
        logger.info("\n" + "=" * 80)
        logger.info("MONITORING RESPONSE (30 seconds)")
        logger.info("=" * 80)
        
        max_wait = 30
        check_interval = 2
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                current_len = len(body_text)
                
                logger.info(f"[{elapsed}s] Body length: {current_len} chars")
                
                if current_len > len(body_text_before) + 200:
                    logger.info("✓ Content changed! Response may be loading...")
                    logger.info(f"   Content preview: {body_text[:300]}")
                
            except Exception as e:
                logger.error(f"Error checking body: {str(e)}")
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        # Final state
        logger.info("\n" + "=" * 80)
        logger.info("FINAL PAGE STATE")
        logger.info("=" * 80)
        
        body_text_final = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Final body length: {len(body_text_final)} chars")
        logger.info(f"Final body preview:\n{body_text_final[:500]}\n...\n{body_text_final[-500:]}")
        
        # Check for response containers
        logger.info("\n" + "=" * 80)
        logger.info("CHECKING DOM STRUCTURE")
        logger.info("=" * 80)
        
        # Look for common response containers
        containers = [
            ("div[class*='message']", "Message divs"),
            ("div[class*='response']", "Response divs"),
            ("div[class*='chat']", "Chat divs"),
            ("div[class*='content']", "Content divs"),
            ("[role='article']", "Article roles"),
            ("[role='region']", "Region roles"),
        ]
        
        for selector, desc in containers:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"✓ Found {len(elements)} {desc}")
                    for i, el in enumerate(elements[:3]):  # Show first 3
                        text = el.text[:100] if el.text else "(empty)"
                        logger.info(f"  [{i}] {text}")
            except Exception as e:
                logger.debug(f"No {desc}: {str(e)}")
        
        # Network events summary
        logger.info("\n" + "=" * 80)
        logger.info("BROWSER LOGS")
        logger.info("=" * 80)
        
        try:
            logs = driver.get_log('browser')
            if logs:
                logger.info(f"Total logs: {len(logs)}")
                network_logs = [log for log in logs if 'network' in log.get('message', '').lower()]
                if network_logs:
                    logger.info(f"Network-related logs: {len(network_logs)}")
                    for log in network_logs[:10]:
                        logger.info(f"  {log['message'][:150]}")
            else:
                logger.info("No browser logs available")
        except:
            logger.info("Could not retrieve browser logs")
        
        # Check JavaScript console for errors
        logger.info("\n" + "=" * 80)
        logger.info("CHECKING BROWSER CONSOLE")
        logger.info("=" * 80)
        
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] in ['SEVERE', 'WARNING']]
        
        if errors:
            logger.info(f"Found {len(errors)} console issues:")
            for log in errors[:5]:
                logger.info(f"[{log['level']}] {log['message'][:100]}")
        else:
            logger.info("No console errors detected")
        
        # Interactive check - keep browser open
        logger.info("\n" + "=" * 80)
        logger.info("BROWSER REMAINS OPEN - Inspect in DevTools to see response")
        logger.info("Press Ctrl+C to close")
        logger.info("=" * 80)
        
        try:
            input("Browser open for inspection. Press Enter to close...")
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        logger.error(f"Test error: {str(e)}", exc_info=True)
    
    finally:
        if driver:
            logger.info("Closing browser...")
            driver.quit()
            logger.info("Browser closed")


if __name__ == "__main__":
    test_qanoonmate_with_network()

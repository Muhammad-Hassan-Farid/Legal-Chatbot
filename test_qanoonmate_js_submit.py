#!/usr/bin/env python3
"""
QanoonMate debug - use JavaScript to submit form and capture response
"""

import os
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

def test_qanoonmate_js_submit():
    """Test QanoonMate with JavaScript submission"""
    driver = None
    try:
        logger.info("Starting QanoonMate JS submission test...")
        
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
        logger.info(f"Initial page: {len(body_before)} chars")
        logger.info(f"Content: {body_before[:150]}")
        
        # Find input with better selector
        logger.info("\nFinding input field...")
        try:
            # Wait for textarea to be present
            wait = WebDriverWait(driver, 15)
            input_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder], textarea"))
            )
            logger.info("✓ Input field found")
        except Exception as e:
            logger.error(f"✗ Could not find input: {e}")
            return
        
        # Type query
        query = "What are fundamental rights in Pakistan?"
        logger.info(f"\nEntering query: {query}")
        input_elem.click()
        time.sleep(0.5)
        input_elem.clear()
        input_elem.send_keys(query)
        logger.info("✓ Query entered")
        
        # Submit using JavaScript to avoid interaction issues
        logger.info("\nSubmitting form with JavaScript...")
        try:
            # Try to find the form and submit it
            driver.execute_script("""
                const form = document.querySelector('form');
                if (form) {
                    form.dispatchEvent(new Event('submit', { bubbles: true }));
                    console.log('Form submitted via dispatch');
                } else {
                    const textarea = document.querySelector('textarea');
                    const event = new KeyboardEvent('keydown', {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true,
                        cancelable: true
                    });
                    textarea.dispatchEvent(event);
                    console.log('Enter key dispatched');
                }
            """)
            logger.info("✓ JavaScript submission executed")
        except Exception as e:
            logger.warning(f"⚠ JS submission failed: {e}, trying Enter key...")
            input_elem.send_keys(Keys.RETURN)
        
        # Monitor response loading
        logger.info("\nMonitoring response (30 seconds)...")
        start_time = time.time()
        max_wait = 30
        last_len = len(body_before)
        stable_count = 0
        
        while (time.time() - start_time) < max_wait:
            time.sleep(1)
            try:
                body = driver.find_element(By.TAG_NAME, "body").text
                current_len = len(body)
                elapsed = int(time.time() - start_time)
                
                if current_len > last_len + 100:
                    logger.info(f"[{elapsed}s] Content growing: {current_len} chars (+{current_len - last_len})")
                    last_len = current_len
                    stable_count = 0
                elif current_len == last_len:
                    stable_count += 1
                    if stable_count >= 5:
                        logger.info(f"[{elapsed}s] Content stable for 5s, size: {current_len}")
                        break
                elif elapsed % 5 == 0:
                    logger.info(f"[{elapsed}s] Waiting... size: {current_len}")
                    
            except Exception as e:
                logger.debug(f"Monitor error: {e}")
        
        # Final analysis
        logger.info("\n" + "="*70)
        logger.info("FINAL ANALYSIS")
        logger.info("="*70)
        
        body_final = driver.find_element(By.TAG_NAME, "body").text
        size_change = len(body_final) - len(body_before)
        
        logger.info(f"\nPage size change: {size_change} chars ({len(body_final)} vs {len(body_before)})")
        logger.info(f"Initial content:\n{body_before}\n")
        logger.info(f"Final content:\n{body_final}")
        
        # Analysis
        logger.info("\n" + "="*70)
        logger.info("ANALYSIS")
        logger.info("="*70)
        
        if "Drafting" in body_final:
            logger.warning("⚠ WARNING: 'Drafting' (button text) still in page")
        
        if size_change > 300:
            logger.info(f"✓ Significant content loaded ({size_change} chars)")
        elif size_change > 0:
            logger.info(f"~ Minor content change ({size_change} chars)")
        else:
            logger.error("✗ NO RESPONSE: Page size unchanged")
            logger.error("Response may be:")
            logger.error("  1. Loaded via API (not in DOM)")
            logger.error("  2. In iframe/shadow DOM (not accessible)")
            logger.error("  3. Still loading after timeout")
            logger.error("  4. Query submission failed")
        
        # Check page structure
        logger.info("\n" + "="*70)
        logger.info("DOM STRUCTURE")
        logger.info("="*70)
        
        # Look for message/response containers
        selectors = {
            "Message containers": "div[class*='message']",
            "Response containers": "div[class*='response']",
            "Chat containers": "div[class*='chat']",
            "Article roles": "[role='article']",
            "Buttons": "button"
        }
        
        for name, sel in selectors.items():
            try:
                count = len(driver.find_elements(By.CSS_SELECTOR, sel))
                logger.info(f"  {name}: {count} elements")
            except:
                pass
        
        # Try to inspect React state if available
        logger.info("\n" + "="*70)
        logger.info("REACT INSPECTION")
        logger.info("="*70)
        
        try:
            react_info = driver.execute_script("""
                const root = document.querySelector('[data-reactroot], #__next, #root');
                return {
                    has_root: !!root,
                    root_tag: root ? root.tagName : null,
                    root_id: root ? root.id : null,
                    root_class: root ? root.className : null,
                    html_size: document.documentElement.outerHTML.length
                };
            """)
            if react_info:
                logger.info(f"✓ React app detected:")
                for key, val in react_info.items():
                    logger.info(f"    {key}: {val}")
        except Exception as e:
            logger.debug(f"React inspection failed: {e}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    
    finally:
        if driver:
            driver.quit()
            logger.info("\n✓ Browser closed")


if __name__ == "__main__":
    test_qanoonmate_js_submit()

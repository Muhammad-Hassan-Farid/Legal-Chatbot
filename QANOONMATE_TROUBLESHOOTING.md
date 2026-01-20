# QanoonMate Response Extraction - Troubleshooting Guide

## Current Status
QanoonMate is returning error messages like "Sorry, there was an error processing your request." 
The system now has better error detection and automatic retry logic.

## Error Message Handling
The scraper now detects error messages and reports them specifically, including:
- Rate limiting errors
- Backend processing errors
- Automated retry (up to 2 attempts with 2-4 second delays)
- User agent rotation to avoid detection

## Quick Diagnosis Steps

### 1. Test QanoonMate Independently
Run the debug script to test QanoonMate scraping in isolation:

```bash
cd /Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot
python test_qanoonmate_debug.py "What are the key labor laws that employers must follow in Pakistan?"
```

**What to look for:**
- Does the browser open successfully?
- Can it find the input field?
- Does it submit the query?
- Does the page content grow (indicating response generation)?
- Can it extract any response text?

### 2. Check Browser Console
If running with headless=False (uncommented in debug script), you can see:
- JavaScript errors
- Network requests
- Page state changes

### 3. Common Issues & Solutions

#### Issue: "Sorry, there was an error processing your request"
**Symptoms:** Error message appears instead of response

**Root Causes:**
- QanoonMate backend experiencing issues
- Rate limiting triggered (too many requests)
- CAPTCHA detection
- Query format not supported

**Solutions:**
1. ✓ Automatic retry logic now implemented
   - Retries up to 2 times with 2-4 second delays
   - Different user agents used per attempt
2. Space out requests - don't spam multiple queries
3. Try simpler, more specific queries
4. Check if QanoonMate website is working directly
5. Wait 5-10 minutes before trying again

#### Issue: "Could not find visible input field"
**Symptoms:** Browser opens but can't locate input field

**Solutions:**
1. QanoonMate may have changed their HTML structure
2. Try inspecting the actual page:
   ```bash
   # Visit the page manually and inspect with DevTools
   # Check what the actual input element selectors are
   ```
3. Update selectors in views.py with new values

#### Issue: Query submitted but no response generated
**Symptoms:** Page doesn't grow, no "Thinking..." indicator appears

**Possible causes:**
- Server-side issue at QanoonMate
- Query not properly submitted
- Page requires additional interaction
- CAPTCHA or rate limiting triggered

**Debug steps:**
- Check browser console for JavaScript errors
- Verify query was actually entered in input
- Look for error messages on page
- Check if IP is rate-limited

#### Issue: Response generated but not extracted
**Symptoms:** Page grows but extraction returns nothing

**Solutions:**
1. Response may be in unexpected location
2. Try extracting full page text:
   ```python
   body_text = driver.find_element(By.TAG_NAME, "body").text
   print(body_text)  # See what's actually there
   ```
3. Update extraction strategies with actual HTML structure

#### Issue: Timeout (wait >50 seconds)
**Symptoms:** Script waits full timeout before proceeding

**Possible causes:**
- Server is slow
- Network latency
- Query complexity requires more processing time

**Solutions:**
- Increase `max_wait_time` from 50 to 60+ seconds
- Check QanoonMate website directly for performance
- Verify internet connection

### 4. Enhanced Debugging

**To see detailed logs:**

1. In `chat/views.py`, ensure logging is configured:
```python
logger.setLevel(logging.DEBUG)  # Show all logs
```

2. Look for these log entries:
- "Starting Selenium browser for QanoonMate scraping..."
- "Found input field with CSS selector: ..."
- "Button clicked successfully"
- "Response ready in X.X seconds"
- "Found response with selector: ..."

**If you don't see these, the script is failing before that point.**

### 5. Manual QanoonMate Testing

Visit https://www.qanoonmate.com/chat manually:

1. **Note the current HTML structure:**
   - Right-click → Inspect Element
   - Find the input field's actual CSS classes/IDs
   - Find the send button's actual selectors
   - Find the response container's structure

2. **Test a query:**
   - Do you get a response?
   - How long does it take?
   - Where does the response appear on page?
   - Any error messages?

3. **Update selectors if needed:**
   - If HTML structure changed, update in `scrape_qanoonmate_response()`

## Code Changes Made

### Latest Improvements (Error Handling & Anti-Bot):

1. **Error Message Detection:**
   - Detects specific error messages from QanoonMate
   - Reports errors back to user with details
   - Stops processing when error detected

2. **Automatic Retry Logic:**
   - Retries up to 2 times with delays
   - 2-4 second delays between attempts
   - Each attempt uses different strategy

3. **Anti-Bot Evasion:**
   - Random user agent rotation
   - 4 different user agents (Chrome, Firefox, macOS, Linux)
   - Blink features disabled
   - Automation detection bypass enabled
   - More human-like interaction timing

4. **Better page diagnostics:**
   - Logs page title, URL, initial text length
   - Helps identify page load issues

5. **Improved wait logic:**
   - Tracks page growth (not just stabilization)
   - Minimum growth requirement (100 chars)
   - Better thinking indicator detection

6. **More verbose logging:**
   - Shows which extraction strategy is attempted
   - Displays sample text for debugging
   - Logs number of lines/elements found

7. **Better aggressive fallback:**
   - Case-insensitive query matching
   - Shows which lines are being skipped and why
   - Better UI element filtering

## Testing Checklist

- [ ] Run debug script - does it find input field?
- [ ] Does query submission work?
- [ ] Does page content grow after submission?
- [ ] Can response be extracted from full page text?
- [ ] Check logs for detailed error information
- [ ] Verify QanoonMate website is working manually
- [ ] Check if there's a rate limit or CAPTCHA

## Next Steps if Still Not Working

1. **Alternative Approach: API Usage**
   - Check if QanoonMate has an official API
   - Might be more reliable than web scraping

2. **Update Selectors**
   - Manually inspect QanoonMate page
   - Get current HTML structure
   - Update CSS/XPath selectors

3. **Increase Timeouts**
   - Some queries may need 60-90 seconds
   - Adjust `max_wait_time` parameter

4. **Different Scraping Library**
   - Consider using Playwright instead of Selenium
   - May have better JavaScript handling

5. **Skip QanoonMate for Now**
   - Focus on Pakistan Law Bot, LawGPT, Lexiber
   - Come back to QanoonMate when issue identified

## Performance Expectations

**Expected times:**
- Page load: 5 seconds
- Response generation: 10-20 seconds
- Total query: 15-30 seconds
- Max allowed: 50 seconds

If consistently taking 50+ seconds, consider increasing timeout or investigating server issues.

## Contact QanoonMate

If debugging reveals website-level issues:
- Check their status page
- Contact support about scraping/API access
- Ask if they have official API for legal chatbot comparisons

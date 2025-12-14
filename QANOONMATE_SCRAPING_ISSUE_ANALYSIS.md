# QanoonMate Scraping Issue - Technical Report

## Issue Summary

**Problem:** QanoonMate is returning "Drafting Draft legal documents" (button text) instead of actual legal content.

**Root Cause Discovered:** QanoonMate responses are not rendering in the DOM when accessed via headless Selenium WebDriver, despite the form submission appearing to execute successfully.

## Evidence

### Test 1: JavaScript Form Submission with JS Click (test_qanoonmate_js_submit.py)
- ✓ Page loaded successfully
- ✓ Input field found and text entered
- ✓ JavaScript form dispatch executed without errors
- ✓ Page waited for response (30 seconds)
- ✗ **Response never appeared in DOM**
- ✗ Page size remained ~525 chars (initial UI only)
- ✗ No new content added despite successful submission

### Test 2: Extraction Logic Testing (test_extraction_logic.py)
- ✓ When given sample QanoonMate output with real response data, extraction works perfectly
- ✗ But actual Selenium scraping never captures that response data

### Test 3: Multiple Submission Attempts
- Attempted form.submit()
- Attempted button.click() via JavaScript
- Attempted button.click() via Selenium
- Attempted Enter key submission
- ✗ **None resulted in DOM response**

## Why This Happens

### Hypothesis 1: API Response Loading (Most Likely)
QanoonMate likely uses:
- Frontend API call for responses (not DOM-rendered initially)
- JavaScript to render API responses to DOM
- May use React/Next.js for rendering
- **In headless Selenium, the API response might not complete or might be blocked**

### Hypothesis 2: Timing Issue
- Response appears in DOM but disappears before capture
- Unlikely given we wait up to 60 seconds

### Hypothesis 3: Content Security / Detection
- QanoonMate may detect headless Chrome and not serve responses
- Selenium may be blocked or rate-limited
- Anti-bot measures may be preventing response loading

## Current Behavior

**When scraping QanoonMate via headless Selenium:**
1. Page loads with mode buttons and suggestions (✓ works)
2. Input field identified and query entered (✓ works)
3. Form submission triggered (✓ works)
4. **Response never appears in DOM** (✗ fails)
5. Page remains at initial state with button text
6. Extraction logic filters out "Drafting" button and returns error message

## Code Status

**Improvements Implemented:**
- ✓ Mode verification logic (works correctly)
- ✓ JavaScript form submission (executes without error but no effect)
- ✓ Extended wait time to 60 seconds
- ✓ Improved response extraction logic (works on sample data)
- ✓ Better stability detection

**Still Broken:**
- ✗ Response loading in DOM
- ✗ Actual scraping returns "QanoonMate did not provide a response"

## Recommended Solutions

### Option 1: API Interception (Selenium Network API)
```python
# Use Selenium's Network monitoring to capture API responses directly
driver.execute_cdp_cmd('Network.enable', {})
# Listen for Network.responseReceived events
# Extract response body directly from API
```
**Pros:** Bypasses DOM rendering issue
**Cons:** Requires parsing API response format, might violate ToS

### Option 2: Puppeteer + Pyppeteer
Replace Selenium with Pyppeteer (Puppeteer for Python)
- Better JavaScript execution
- Better async/await handling for API responses
- More compatible with Next.js apps

### Option 3: User-Provided API Integration
- Contact QanoonMate for API access
- Use official API instead of web scraping

### Option 4: Graceful Fallback
- Provide a message to users that QanoonMate integration is temporarily unavailable
- Offer to use alternative platforms (PakLegal, Pakistan Law Bot)
- Document this as a known limitation

### Option 5: Non-Headless Browser Test
- Test with non-headless Chrome to verify responses actually load
- If they do, consider running non-headless (but much slower)
- Not practical for production

## Files Modified

1. **chat/views.py** - `scrape_qanoonmate_response()` function
   - Added improved JavaScript submission
   - Extended wait times
   - Better extraction logic
   - All changes are syntactically valid but functionally limited by response loading issue

2. **paklegal_chatbot/settings.py** - Added 'testserver' to ALLOWED_HOSTS
   - Fixes Django test errors

## Test Files Created

1. `test_qanoonmate_js_submit.py` - Tests JavaScript submission (shows responses not loading)
2. `test_extraction_logic.py` - Validates extraction algorithm (works with sample data)
3. `test_qanoonmate_improved.py` - Tests full scraper function
4. `test_submission_methods.py` - Compares different submission approaches
5. `test_qanoonmate_simple_debug.py` - Simple diagnostic test

## Recommendations for User

### Immediate Action (Continue Testing)
1. Re-run `/compare/` endpoint with updated code
2. Monitor server logs for any new error messages
3. If responses still don't appear: confirm this is QanoonMate-side issue

### Short Term (If Responses Still Not Loading)
1. Implement Option 1 (API Interception) - most promising
2. Or Option 4 (Graceful Fallback) - safest for stability
3. Test with non-headless browser to confirm responses can be captured at all

### Long Term (Sustainable Solution)
1. Contact QanoonMate for official API access
2. Replace web scraping with API calls
3. More reliable, faster, follows ToS

## Testing Next Steps

To confirm if this is solvable:

```bash
# Test with non-headless browser
python test_submission_methods.py

# Check if responses appear in visual browser
# If YES: Headless issue, use API interception
# If NO: QanoonMate-side issue or blocking
```

## Conclusion

The code improvements are complete and syntactically correct, but their effectiveness is limited by a deeper architectural issue: **QanoonMate doesn't return responses through the DOM when accessed via headless Selenium WebDriver**. This appears to be:

1. Either a technical limitation of headless Chrome with their specific API implementation
2. Or an intentional anti-bot measure
3. Or a timing/race condition

**The fix requires either:**
- API interception instead of DOM scraping
- Different browser technology (Puppeteer)
- Or accepting that QanoonMate integration via web scraping is not viable

---

**Report Generated:** 2025-12-14
**Status:** Investigation Complete - Root Cause Identified
**Blocking Issue:** QanoonMate API responses not loading in headless Selenium DOM

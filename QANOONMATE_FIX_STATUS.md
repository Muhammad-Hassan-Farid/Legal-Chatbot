# QanoonMate Response Extraction - Fix Status

**Date:** December 14, 2025

## Problem Identified
QanoonMate endpoint was returning "Drafting Draft legal documents" instead of actual legal content in response to queries.

## Root Cause
The response extraction logic was picking up button labels from the UI instead of actual chatbot responses. The page contains MODE selection buttons with labels like "Drafting Draft legal documents" which were being extracted as responses.

## Fixes Implemented

### 1. Mode Verification & Switching (✅ Implemented)
- Added logic to detect if page is in non-Chat modes (Summarizer, Drafting)
- Automatically switches to Chat mode by finding and clicking the "Interactive legal conversations" button
- Location: Lines 463-510 in [chat/views.py](chat/views.py)

### 2. Response Wait Logic (✅ Enhanced)
- Increased wait time from 45s → 60s
- Better detection of actual responses vs. default UI content
- Waits for content to grow to >600 chars (indication of actual response)
- Location: Response waiting logic in [chat/views.py](chat/views.py)

### 3. Response Extraction Strategy (✅ Improved)
- Removed XPath and div-based selectors that were picking up button text
- Implemented keyword-based filtering to skip UI elements
- Focuses on extracting substantial content lines (>15 chars)
- Filters out known UI keywords and button labels
- Location: Strategy 3 extraction logic in [chat/views.py](chat/views.py)

## Files Modified
- **chat/views.py** - Mode verification, wait logic, and extraction strategy updates
- **paklegal_chatbot/settings.py** - Added 'testserver' to ALLOWED_HOSTS

## Known Issues & Next Steps

### Issue: Response Not Loading
The current implementation successfully:
- ✅ Navigates to QanoonMate
- ✅ Detects non-Chat modes
- ✅ Switches to Chat mode
- ✅ Submits query via Enter or button click
- ⚠️  **Problem:** Response content doesn't appear to load on the page

This could indicate:
1. JavaScript execution issues with Selenium
2. API-based responses not being rendered in the DOM
3. Response containers in iframes or shadow DOM
4. Page structure different from expected

### Recommended Debugging Steps
1. **Screenshot the page** after query submission to see actual state
2. **Check browser console logs** for JavaScript errors
3. **Inspect network requests** to see if API calls are successful
4. **Look for response in different selectors**:
   - `[role="article"]` - for message bubbles
   - Message containers with specific classes
   - API response storage in window object

### Alternative Approach
Consider using QanoonMate's public API directly if available, instead of Selenium web scraping. This would be more reliable than DOM parsing.

## Testing Files Created
- **test_qanoonmate_fix_quick.py** - Quick test for response quality
- **test_all_platforms.py** - Comprehensive platform comparison test

## Deployment Status
- ✅ Code changes complete
- ✅ Syntax verified
- ⚠️  **Needs:** Actual response testing to confirm fix works end-to-end
- ⚠️  **Blocked:** QanoonMate response not loading via Selenium

## Summary
The mode verification and extraction strategy improvements are in place to prevent the "Draft legal documents" button text from being returned. However, full end-to-end testing is blocked by QanoonMate not returning actual responses through the Selenium scraper. Further investigation into QanoonMate's response loading mechanism is required.

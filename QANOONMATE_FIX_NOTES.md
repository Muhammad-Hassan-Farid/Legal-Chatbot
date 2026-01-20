# QanoonMate Response Extraction Fix

## Problem
QanoonMate was not providing responses in the chatbot comparison tests. The logs showed:
- `"QanoonMate did not provide a response to the query."`
- Despite the Selenium browser successfully loading the page and interacting with it

## Root Cause Analysis
The response extraction logic had several issues:
1. **Timeout Detection**: The original wait logic (35 seconds) used 1-second intervals, potentially missing the response or timing out
2. **Selector Strategies**: The XPath and CSS selectors were too rigid and didn't adapt to QanoonMate's actual HTML structure
3. **Fallback Logic**: The intelligent extraction fallback was limited to only 30 divs and had strict filtering criteria
4. **Response Validation**: The validation logic rejected valid responses if they didn't meet exact length/format requirements

## Solutions Implemented

### 1. Improved Wait Logic
- **Increased timeout**: From 35 to 50 seconds for better reliability
- **Smaller check interval**: From 1 second to 0.5 seconds for faster detection
- **Lower threshold**: Changed response length threshold from 300/350 to 200 characters
- **Better detection**: Added multiple detection strategies:
  - Check for page stabilization (content not changing)
  - Monitor removal of "Thinking", "In progress", "Analyzing" indicators
  - Validate actual content growth

```python
max_wait_time = 50  # Increased from 35
check_interval = 0.5  # Reduced from 1
response_length_threshold = 200  # More lenient threshold
```

### 2. Enhanced Selector Coverage
- **XPath selectors**: Added debug logging to understand which selectors match
- **CSS selectors**: Added more specific selectors including:
  - `div[class*="answer"]`
  - `main > div:last-of-type`
- **Better element filtering**: More robust logic to skip suggestions and UI text

### 3. Improved Fallback Extraction
- **Larger search scope**: Check last 50 divs instead of 30
- **Smarter filtering**: Added "Legal" keyword prioritization for legal content
- **Better UI keyword filtering**: Expanded list of UI keywords to filter:
  - "Login", "Sign Up", "Did you know"
  - "Web Search", "Audio Search"
- **More lenient validation**: Accept responses > 50 chars instead of strict > 60 chars

### 4. Aggressive Final Fallback
- **New strategy**: Line-by-line text extraction after finding the query
- **Progressive collection**: Accumulate all content after the query is found
- **Smart filtering**: Skip known UI elements while collecting response
- **Fallback depth**: Up to 4 extraction strategies before giving up

### 5. Enhanced Logging
- Added debug logs to show:
  - Number of elements found by each selector
  - Which extraction strategy succeeded
  - Response length at each stage
  - Clear indication of what was filtered and why

## Key Code Changes

### File: `chat/views.py`

1. **`scrape_qanoonmate_response()` function**:
   - Enhanced wait logic with better detection
   - More comprehensive selector strategies
   - Improved fallback extraction mechanisms
   - Better error logging and debugging

2. **Extraction Strategy Flow**:
   ```
   1. Wait for response (up to 50 seconds)
   2. Try XPath selectors (bot messages, articles, etc.)
   3. Try CSS selectors (div classes, roles)
   4. Try intelligent div extraction (last 50 divs)
   5. Try aggressive line-by-line extraction
   6. Return meaningful message if all fail
   ```

## Testing Recommendations

1. **Test with various query types**:
   - Legal questions (fundamental rights, laws)
   - Procedural questions
   - Case law inquiries

2. **Monitor logs for**:
   - Which extraction strategy succeeds
   - Response lengths and content quality
   - Wait times until response is ready

3. **Expected improvements**:
   - QanoonMate should now consistently provide responses
   - Better handling of page structure variations
   - More reliable response extraction
   - Improved error messages when actual failures occur

## Performance Impact
- **Slightly longer wait times** (50 seconds max vs 35) - better reliability
- **More frequent checks** (0.5s intervals) - faster detection when ready
- **Better resource usage** - aggressive fallback prevents hanging

## Future Improvements
- Consider switching from Selenium to direct API calls if available
- Add response caching to avoid repeated identical queries
- Implement response quality scoring for better filtering
- Add periodic updates to selector strategies based on actual HTML structure changes

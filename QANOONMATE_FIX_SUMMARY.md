# QanoonMate Scraping - Fix Summary

## Date: December 14, 2025

## Issues Identified

1. **Inefficient Page Loading Wait**: Using fixed `time.sleep(5)` without checking if elements are ready
2. **Poor Element Detection**: CSS selectors too specific, missing fallback strategies
3. **Weak Response Waiting Logic**: Only checking page length, not actual response completion indicators
4. **Brittle Response Extraction**: Multiple XPath selectors that may fail on page changes
5. **False Suggestions as Responses**: Not properly filtering suggestion cards from actual responses

## Solutions Implemented

### 1. **Improved Page Load Wait (Lines 384-395)**

**Before:**
```python
time.sleep(5)  # Fixed wait - unreliable
```

**After:**
```python
wait = WebDriverWait(driver, 15)
try:
    input_field = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, input[type='text']"))
    )
except:
    logger.warning("Timeout waiting for input field, proceeding anyway")
    time.sleep(2)
```

**Benefits:**
- Waits only as long as needed (up to 15 seconds)
- More reliable for dynamic JavaScript-heavy pages
- Falls back gracefully if element isn't found

---

### 2. **Better Element Detection Strategy (Lines 399-445)**

**Before:**
```python
# Only tried CSS selectors in order, no fallback if none worked
for selector in css_selectors:
    # ...find element
```

**After:**
```python
# Three-tier strategy:
# 1. Use WebDriverWait for textarea (most common)
# 2. Use WebDriverWait for text input
# 3. Use WebDriverWait for elements by placeholder
# 4. Fallback to tag-by-tag search
```

**Benefits:**
- Handles different QanoonMate versions
- More resilient to CSS class changes
- Explicit wait for clickability ensures interactivity

---

### 3. **Robust Text Input (Lines 447-468)**

**Before:**
```python
try:
    input_field.send_keys(query)
except:
    driver.execute_script(f"arguments[0].value = `{query}`", input_field)
    # Crude escape handling
```

**After:**
```python
try:
    input_field.send_keys(Keys.CONTROL + 'a')  # Clear first
    input_field.send_keys(query)
except Exception as e:
    # Proper escape of backslashes, backticks, quotes
    safe_query = query.replace('\\', '\\\\').replace('`', '\\`').replace('"', '\\"')
    driver.execute_script(f"""
        const elem = arguments[0];
        elem.value = "{safe_query}";
        elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
        elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
    """, input_field)
```

**Benefits:**
- Proper text escaping prevents JavaScript injection issues
- Triggers input/change events for reactive frameworks
- Clears field first to avoid duplicate text

---

### 4. **Smarter Send Button Click (Lines 470-531)**

**Before:**
```python
# Simple try once, might fail silently
button.click()
```

**After:**
```python
# Multiple strategies:
# 1. Try CSS selector patterns (aria-label, class patterns)
# 2. Fallback to find last visible button
# 3. Try form submission
# 4. Try Enter key as last resort
```

**Benefits:**
- Handles different button placements
- Uses JavaScript click as fallback
- Proper error messaging for debugging

---

### 5. **Intelligent Response Waiting (Lines 533-571)**

**Before:**
```python
# Only check page length consistency
if current_length == previous_page_length:
    stable_count += 1
```

**After:**
```python
# Multiple indicators:
# 1. Content stabilization (text not changing)
# 2. "Thinking..." disappears from page
# 3. Track consecutive stable checks
# 4. 40-second max timeout (increased from 35)
```

**Benefits:**
- More accurate detection of response completion
- Handles different response generation speeds
- Reduces false positives for incomplete responses

---

### 6. **Multi-Strategy Response Extraction (Lines 578-654)**

Three extraction strategies now in order:

#### Strategy 1: XPath Search
```python
# Look for standard chat patterns:
# - div.message:not(.user)
# - div.bot
# - div.response
# - Elements with article role
```

#### Strategy 2: Text Div Search
```python
# Search last 50 divs for substantial text
# Must be >100 chars and not contain UI keywords
```

#### Strategy 3: Full Page Text
```python
# Split body text by newlines
# Filter for paragraphs >80 chars
# Exclude UI elements
```

**Benefits:**
- Handles different QanoonMate UI versions
- Falls back gracefully if one strategy fails
- More likely to extract real response vs. suggestions

---

### 7. **Better Suggestion Detection (Lines 583-610)**

**Before:**
```python
suggestion_keywords = ["try asking", "business registration", ...]
if any(keyword in lowered for keyword in suggestion_keywords):
    return True
```

**After:**
```python
def looks_like_suggestion(text: str) -> bool:
    if not text:
        return True
    lowered = text.lower()
    # Check keywords
    if any(keyword in lowered for keyword in suggestion_keywords):
        return True
    # Check format patterns
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lowered.startswith("try asking"):
        return True
    # Check if it's just a few short lines
    if len(lines) >= 3 and all(len(line) < 80 for line in lines):
        return True
    return False
```

**Benefits:**
- More comprehensive suggestion detection
- Looks at both content AND format
- Reduces false positives for real legal responses

---

### 8. **Final Response Validation (Lines 656-681)**

**Before:**
```python
if len(response_text) < 100 and looks_like_suggestion(response_text):
    return "No response..."
```

**After:**
```python
# Multiple validation checks:
if not response_text:
    return error message
if len(response_text) < 100 and looks_like_suggestion():
    return error message
# Normalize whitespace
response_text = normalize()
# Add paragraph breaks
if len > 200:
    add breaks
# Final length check
if len < 20:
    return error message
```

**Benefits:**
- Comprehensive validation prevents bad responses
- Better formatting for readability
- Clear error messages for debugging

---

## Testing Recommendations

1. **Test with various queries:**
   - Short queries: "What is the Constitution?"
   - Long queries: Complex legal questions
   - Urdu queries: If QanoonMate supports them

2. **Monitor logs** for:
   - Which extraction strategy succeeds
   - Response wait times
   - Any element detection issues

3. **Performance metrics:**
   - Average response time
   - Success rate across multiple queries
   - Consistency of response quality

---

## Files Modified

- `chat/views.py` - Lines 359-681 (scrape_qanoonmate_response function)

## Key Parameters

- **Page load wait timeout**: 15 seconds (EC.presence_of_element_located)
- **Response wait timeout**: 40 seconds (max)
- **Response check interval**: 1.5 seconds
- **Min stable checks**: 3 consecutive identical responses
- **Min response length**: 100 characters
- **Suggestion detection**: keyword-based + format-based


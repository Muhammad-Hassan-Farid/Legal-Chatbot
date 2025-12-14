from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from chat.services import get_rag_chain
import json
import logging
import whisper
from gtts import gTTS
import io
import os
from langdetect import detect, DetectorFactory
import re
from html.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Set seed for consistent language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

# Global cache for Whisper model
_whisper_model = None
_whisper_model_lock = None


def get_whisper_model():
    """
    Get cached Whisper model. Lazy loads on first use.
    Uses threading lock to ensure thread-safe loading.
    """
    global _whisper_model, _whisper_model_lock
    
    if _whisper_model_lock is None:
        import threading
        _whisper_model_lock = threading.Lock()
    
    if _whisper_model is None:
        with _whisper_model_lock:
            if _whisper_model is None:  # Double check
                logger.info("Lazy loading Whisper model for first time...")
                _whisper_model = whisper.load_model("base", device="cpu")
                logger.info("Whisper model loaded and cached")
    
    return _whisper_model


def extract_text_from_markdown(text):
    """
    Extract plain text from markdown response.
    Removes markdown syntax and HTML tags to reduce TTS synthesis time.
    """
    # Remove markdown code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove inline code formatting
    text = re.sub(r'`([^`]*)`', r'\1', text)
    
    # Remove bold/italic markdown
    text = re.sub(r'\*\*([^\*]*)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]*)\*', r'\1', text)
    text = re.sub(r'__([^_]*)__', r'\1', text)
    text = re.sub(r'_([^_]*)_', r'\1', text)
    
    # Remove markdown links
    text = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', text)
    
    # Remove markdown headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown lists
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\n+', '\n', text)
    text = text.strip()
    
    return text


def normalize_response_structure(text, source="generic"):
    """
    Normalize response structure from any platform to ensure consistent formatting.
    
    Ensures:
    - Proper paragraph breaks
    - Consistent section formatting
    - Organized content structure
    - Better readability
    
    Args:
        text (str): Response text from any platform
        source (str): Source platform ('paklegal', 'pakistanlaw', 'qanoonmate', 'generic')
    
    Returns:
        str: Normalized response with consistent structure
    """
    if not text:
        return ""
    
    # Step 1: Clean up text
    text = text.strip()
    
    # Step 2: Normalize line breaks - remove excess whitespace while preserving structure
    # Replace multiple line breaks with double line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Step 3: Ensure proper spacing around common section markers
    # Add breaks before article/section references
    text = re.sub(r'(\w)\n(Article|Section|Clause|Rule|Part)', r'\1\n\n\2', text)
    
    # Step 4: Format bullet points properly
    # Ensure bullet points have proper spacing
    text = re.sub(r'\n([-•*])\s+', r'\n\n\1 ', text)
    
    # Step 5: Format numbered lists properly
    text = re.sub(r'\n(\d+)\.?\s+', r'\n\n\1. ', text)
    
    # Step 6: Add proper spacing around legal references
    # Ensure legal article references are properly spaced
    text = re.sub(r'([\.!?])\s+(Article|Section|Art\.|Sec\.)', r'\1\n\n\2', text)
    
    # Step 7: Clean up spacing around parentheses (case law citations)
    text = re.sub(r'\s+\(', ' (', text)
    text = re.sub(r'\)\s+', ') ', text)
    
    # Step 8: Ensure consistent paragraph spacing
    lines = text.split('\n')
    structured_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Check if this is a header/section title (all caps or starts with numbers)
        is_header = (line.isupper() and len(line) > 3) or line.startswith(('Article', 'Section', 'Part', '1.', '2.', '3.'))
        is_bullet = line.startswith(('-', '•', '*'))
        is_numbered = bool(re.match(r'^\d+\.', line))
        
        # Add extra space before headers and numbered items
        if structured_lines and (is_header or is_numbered):
            structured_lines.append('')  # Add blank line before
        
        structured_lines.append(line)
    
    # Step 9: Join lines with proper spacing
    result = '\n'.join(structured_lines)
    
    # Step 10: Final cleanup - ensure double line breaks between paragraphs
    result = re.sub(r'\n\n\n+', '\n\n', result)
    
    return result.strip()


def landing(request):
    """Landing page with hero section"""
    return render(request, 'landing.html')


def chat_page(request):
    """Chat interface page"""
    return render(request, 'chat.html')


def detect_language(text):
    """
    Detect the language of the input text.
    Returns language code: 'ur' for Urdu, 'en' for English, etc.
    """
    try:
        lang = detect(text)
        logger.info(f"Detected language: {lang}")
        return lang
    except Exception as e:
        logger.warning(f"Language detection failed: {str(e)}, defaulting to English")
        return 'en'


@csrf_exempt
@require_http_methods(["POST", "GET"])
def chat_api(request):
    """
    API endpoint for chat responses.
    Optimized for low latency: returns response immediately with first synthesis chunk.
    """
    try:
        if request.method == 'POST':
            # Handle form data
            user_input = request.POST.get('msg', '')
            input_language = request.POST.get('lang', 'en')
            voice_response = request.POST.get('voice', 'false').lower() == 'true'  # Whether to synthesize voice
        else:
            # Handle GET request
            user_input = request.GET.get('msg', '')
            input_language = request.GET.get('lang', 'en')
            voice_response = request.GET.get('voice', 'false').lower() == 'true'
        
        if not user_input:
            return HttpResponse('No message provided', status=400)
        
        logger.info(f"Processing user input in language: {input_language}, voice_response: {voice_response}")
        
        # Get RAG chain and invoke
        rag_chain = get_rag_chain()
        response = rag_chain.invoke({"input": user_input})
        
        # Handle response - could be string or dict
        if isinstance(response, dict):
            answer = response.get("answer", str(response))
        else:
            answer = str(response)
        
        logger.info(f"RAG response generated, length: {len(answer)}, language: {input_language}")
        
        # If voice response requested, return early with text + URL for async synthesis
        if voice_response:
            # Extract plain text for TTS (will be synthesized on frontend or async)
            plain_text = extract_text_from_markdown(answer)
            
            return JsonResponse({
                'answer': answer,
                'plain_text': plain_text,  # For voice synthesis
                'language': input_language,
                'synthesize_url': '/synthesize/'  # Frontend will use this for async synthesis
            })
        
        # Return response with language info
        return JsonResponse({
            'answer': answer,
            'language': input_language
        })

    except Exception as e:
        logger.exception(f"Error in chat_api: {str(e)}")
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def transcribe_audio(request):
    """
    API endpoint for transcribing audio with language detection.
    Optimized: Uses cached Whisper model for faster repeated transcriptions.
    """
    logger.info("Transcribe audio endpoint called")
    
    if 'audio' not in request.FILES:
        logger.error("No audio file in request")
        return JsonResponse({'error': 'No audio file found'}, status=400)

    try:
        audio_file = request.FILES['audio']
        logger.info(f"Audio file received: {audio_file.name}, size: {audio_file.size}")
        
        # Save the uploaded file temporarily with a unique name
        temp_filename = f"temp_audio_{os.getpid()}_{id(audio_file)}.wav"
        with open(temp_filename, "wb+") as f:
            for chunk in audio_file.chunks():
                f.write(chunk)
        
        logger.info(f"Audio file saved to: {temp_filename}")

        # Transcribe using cached Whisper model
        logger.info("Getting cached Whisper model...")
        model = get_whisper_model()
        logger.info("Whisper model ready, transcribing...")
        
        # Whisper with language detection - optimized settings
        # Use language detection without forcing a language
        result = model.transcribe(
            temp_filename,
            language=None,  # Auto-detect language
            fp16=False,     # Use fp32 for stability, can switch to True for speed
            verbose=False   # Reduce logging overhead
        )
        transcript = result["text"].strip()
        detected_lang = result.get("language", "en")
        
        # Map Whisper language code to standard code
        lang_map = {
            'urdu': 'ur',
            'ur': 'ur',
            'english': 'en',
            'en': 'en',
            'hindi': 'hi',
            'hi': 'hi',
            'pashto': 'ps',
            'ps': 'ps',
            'punjabi': 'pa',
            'pa': 'pa',
        }
        detected_lang = lang_map.get(detected_lang.lower(), detected_lang)
        
        logger.info(f"Transcription successful: {transcript[:50]}..., language: {detected_lang}")
        
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            logger.info(f"Cleaned up temp file: {temp_filename}")
        
        return JsonResponse({
            'transcript': transcript,
            'language': detected_lang
        })

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Failed to transcribe audio: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def synthesize_speech(request):
    """
    API endpoint for synthesizing speech in the detected language.
    Optimized: Uses plain text input to reduce synthesis time.
    """
    logger.info("Synthesize speech endpoint called")
    
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
        
        # Accept either 'text' or 'plain_text' for flexibility
        text = data.get('plain_text') or data.get('text', '')
        text = text.strip()
        language = data.get('language', 'en')

        if not text:
            logger.error("No text provided for synthesis")
            return JsonResponse({'error': 'No text provided'}, status=400)

        # Limit text length for faster synthesis (2000 chars ~= 2-3 min audio)
        max_length = 2000
        if len(text) > max_length:
            logger.info(f"Truncating text from {len(text)} to {max_length} chars for synthesis")
            text = text[:max_length].rsplit(' ', 1)[0] + '...'
        
        logger.info(f"Generating speech for {len(text)} chars in language: {language}")
        
        # Map language codes to gTTS language codes
        lang_map = {
            'ur': 'ur',      # Urdu
            'urdu': 'ur',
            'en': 'en',      # English
            'english': 'en',
            'hi': 'hi',      # Hindi
            'hindi': 'hi',
            'ps': 'ps',      # Pashto
            'pashto': 'ps',
            'pa': 'pa',      # Punjabi
            'punjabi': 'pa',
        }
        
        tts_lang = lang_map.get(language.lower(), 'en')
        logger.info(f"Using TTS language: {tts_lang}")
        
        # Generate speech using gTTS in detected language
        try:
            # Use slow=False for faster synthesis
            tts = gTTS(text=text, lang=tts_lang, slow=False)
        except Exception as e:
            logger.warning(f"TTS failed for language {tts_lang}, falling back to English: {str(e)}")
            tts = gTTS(text=text, lang='en', slow=False)
            tts_lang = 'en'
        
        # Save to memory file
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        audio_bytes = mp3_fp.getvalue()
        logger.info(f"Speech synthesis successful: {len(audio_bytes)} bytes in language: {tts_lang}")
        
        response = HttpResponse(audio_bytes, content_type='audio/mpeg')
        response['Content-Disposition'] = 'inline; filename="response.mp3"'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error during speech synthesis: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Failed to generate speech: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def compare_with_qanoonmate(request):
    """
    Fetches response from QanoonMate chatbot using Selenium web scraping.
    Visits their website, enters the query, and extracts the response.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        logger.info(f"Fetching QanoonMate response for: {message[:100]}")
        
        # Fetch from QanoonMate website using Selenium
        qanoonmate_response = scrape_qanoonmate_response(message)
        
        # Normalize response structure for consistent formatting
        qanoonmate_response = normalize_response_structure(qanoonmate_response, source="qanoonmate")
        
        logger.info(f"QanoonMate response length: {len(qanoonmate_response)}")
        
        return JsonResponse({
            'qanoonmate_response': qanoonmate_response,
            'bot_name': 'QanoonMate',
            'success': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in QanoonMate scraping: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'QanoonMate fetch error: {str(e)}'}, status=500)


def scrape_qanoonmate_response(query):
    """
    Uses Selenium to visit QanoonMate chatbot, enter query, and extract response.
    Enhanced with better element interaction strategies to handle QanoonMate's dynamic UI.
    """
    driver = None
    try:
        logger.info("Starting Selenium browser for QanoonMate scraping...")
        
        # Chrome options for headless browser
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Initialize Chrome driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info("Browser opened, navigating to QanoonMate...")
        driver.get("https://www.qanoonmate.com/chat")
        
        # Wait for page to fully load using WebDriverWait instead of fixed sleep
        # This is more reliable for dynamic Next.js applications
        wait = WebDriverWait(driver, 15)
        logger.info("Waiting for QanoonMate page to load...")
        
        # IMPORTANT: The Chat input field is available in Chat mode (the default)
        # Make sure we're in Chat mode and not in Summarizer or Drafting modes
        # The page auto-loads in Chat mode, but we add extra logic for safety
        logger.info("Ensuring proper mode state...")
        try:
            # Wait for the Chat interface to be ready
            # Look for any button that suggests we might be in a different mode
            time.sleep(1)  # Brief wait for page to stabilize
            
            # Check if we can find the "Drafting" text - if it appears in the page title/content,
            # we might be in the wrong mode. Try to switch back to Chat mode.
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "Summarizer" in body_text or "Drafting" in body_text:
                logger.info("Non-Chat mode detected, attempting to switch to Chat...")
                # Look for MODE/selection buttons and select Chat
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    try:
                        btn_text = btn.text.strip()
                        # Look for button with Chat-related text that's also clickable
                        if "Interactive legal conversations" in btn.text:
                            logger.info("Found Chat mode option, clicking...")
                            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            time.sleep(0.3)
                            btn.click()
                            logger.info("Switched to Chat mode")
                            time.sleep(1)
                            break
                    except:
                        continue
        except Exception as e:
            logger.warning(f"Could not verify/switch mode: {str(e)}")
        
        # Wait for input field to be present and clickable
        try:
            input_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, input[type='text']"))
            )
            logger.info("Input field detected")
        except:
            logger.warning("Timeout waiting for input field, proceeding anyway")
            time.sleep(2)
        
        # Multiple selector strategies to find input field - improved version
        input_field = None
        
        # Strategy 1: Use explicit waits for better element finding
        wait = WebDriverWait(driver, 10)
        
        # Try textarea first (most common for chat apps)
        try:
            logger.info("Trying to find textarea...")
            input_field = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea"))
            )
            logger.info("Found textarea element")
        except:
            logger.debug("Textarea not found, trying input fields...")
        
        # Try text input fields
        if not input_field:
            try:
                logger.info("Trying to find text input...")
                input_field = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']"))
                )
                logger.info("Found text input element")
            except:
                logger.debug("Text input not found...")
        
        # Strategy 2: Try finding by placeholder text
        if not input_field:
            logger.info("Trying to find by placeholder...")
            try:
                input_field = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[placeholder*='ask'], [placeholder*='message'], [placeholder*='query']"))
                )
                logger.info("Found input by placeholder")
            except:
                logger.debug("Placeholder search failed...")
        
        # Strategy 3: If CSS didn't work, try finding any visible input/textarea
        if not input_field:
            logger.warning("CSS selectors didn't find input, trying tag name approach...")
            for tag in ['textarea', 'input']:
                try:
                    elements = driver.find_elements(By.TAG_NAME, tag)
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.get_attribute('type') != 'hidden':
                                input_field = elem
                                logger.info(f"Found visible {tag} element")
                                break
                        except:
                            continue
                    if input_field:
                        break
                except:
                    continue
        
        if input_field is None:
            raise Exception("Could not find visible input field on QanoonMate page")
        
        logger.info(f"Found input field, preparing to enter query: {query}")
        
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
        time.sleep(0.5)
        
        # Click to focus using JavaScript (most reliable)
        driver.execute_script("""
            arguments[0].focus();
            arguments[0].click();
        """, input_field)
        
        time.sleep(0.5)
        
        # Clear the field using JavaScript
        driver.execute_script("arguments[0].value = '';", input_field)
        time.sleep(0.3)
        
        # Type text using send_keys with proper error handling
        try:
            # Clear any existing text first
            input_field.send_keys(Keys.CONTROL + 'a')
            time.sleep(0.2)
            input_field.send_keys(query)
            logger.info("Text entered successfully via send_keys")
        except Exception as e:
            # If send_keys fails, use JavaScript
            logger.warning(f"send_keys failed ({str(e)}), using JavaScript to enter text")
            # Properly escape backticks and quotes in JavaScript
            safe_query = query.replace('\\', '\\\\').replace('`', '\\`').replace('"', '\\"')
            driver.execute_script(f"""
                const elem = arguments[0];
                elem.value = "{safe_query}";
                elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
            """, input_field)
        
        time.sleep(0.5)
        
        # Find and click send button
        button = None
        button_found = False
        
        # Try to find submit button with various selectors
        button_selectors = [
            'button[type="submit"]',
            'button[aria-label*="send"]',
            'button[aria-label*="Send"]',
            'button:has(svg)',  # Button with icon
            'button[class*="send"]',
            'button[class*="submit"]',
            'button[class*="action"]',
        ]
        
        logger.info("Looking for send button...")
        for selector in button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    try:
                        if btn.is_displayed():
                            button = btn
                            logger.info(f"Found button with selector: {selector}")
                            button_found = True
                            break
                    except:
                        continue
                if button_found:
                    break
            except:
                continue
        
        # Fallback: Find the last visible button (usually send button in chat UIs)
        if not button:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in reversed(buttons):
                    try:
                        if btn.is_displayed():
                            button = btn
                            logger.info("Found last visible button as fallback")
                            break
                    except:
                        continue
            except:
                pass
        
        # Try to submit the form using JavaScript (most reliable for Next.js apps)
        logger.info("Submitting form with JavaScript...")
        try:
            # First try to find a submit button and click it
            driver.execute_script("""
                // Try to find and click the send button
                const sendButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                    btn.textContent.toLowerCase().includes('send') || 
                    btn.textContent.toLowerCase().includes('submit') ||
                    btn.getAttribute('aria-label') && btn.getAttribute('aria-label').toLowerCase().includes('send')
                );
                if (sendButtons.length > 0) {
                    sendButtons[0].click();
                    console.log('Send button clicked');
                } else {
                    // Fallback: submit form
                    const form = document.querySelector('form');
                    if (form) {
                        form.dispatchEvent(new Event('submit', { bubbles: true }));
                        console.log('Form submitted');
                    } else {
                        // Last resort: trigger Enter key on textarea
                        const textarea = document.querySelector('textarea');
                        if (textarea) {
                            textarea.dispatchEvent(new KeyboardEvent('keydown', { 
                                key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true 
                            }));
                            console.log('Enter key triggered on textarea');
                        }
                    }
                }
            """)
            logger.info("Form submission executed via JavaScript")
        except Exception as e:
            logger.warning(f"JavaScript submission had error: {str(e)}, will try button click...")
            
            # Try to click the send button directly
            if button:
                try:
                    driver.execute_script("arguments[0].click();", button)
                    logger.info("Button clicked via JavaScript execute_script")
                except Exception as e2:
                    logger.warning(f"Button click failed: {str(e2)}")
            else:
                try:
                    # Last resort: press Enter
                    input_field.send_keys(Keys.RETURN)
                    logger.info("Submitted via Enter key")
                except Exception as e3:
                    logger.warning(f"Could not submit query: {str(e3)}")
        
        # Wait for response with improved logic
        logger.info("Waiting for QanoonMate response...")
        
        # Initial wait for response to appear
        time.sleep(2)
        
        response_text = None
        max_wait_time = 60  # Wait up to 60 seconds for response
        check_interval = 0.5  # Check more frequently
        elapsed_time = 0
        
        # Track content changes
        prev_body_len = 0
        stable_count = 0
        response_detected = False
        max_body_len = 0
        
        while elapsed_time < max_wait_time:
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                current_len = len(body_text)
                max_body_len = max(max_body_len, current_len)
                
                # Initial page is around 300-600 chars, response should add 500+ chars
                # But be more aggressive - even 300+ chars above initial suggests response
                if current_len > 900 and not response_detected:  # Response loaded (initial ~400 + response 500+)
                    logger.info(f"Response detected at {elapsed_time:.1f}s: {current_len} chars (initial was ~500)")
                    response_detected = True
                    stable_count = 0
                
                if response_detected:
                    # Once response is detected, wait for it to stabilize
                    if current_len == prev_body_len:
                        stable_count += 1
                        if stable_count >= 4:  # 2 seconds of no change = stable
                            logger.info(f"Response stable at {elapsed_time:.1f}s, final size: {current_len}")
                            break
                    else:
                        stable_count = 0
                        logger.debug(f"[{elapsed_time:.1f}s] Content: {current_len} chars")
                
                prev_body_len = current_len
                
            except Exception as e:
                logger.debug(f"Wait error: {str(e)}")
            
            time.sleep(check_interval)
            elapsed_time += check_interval
        
        logger.info(f"Response wait completed after {elapsed_time:.1f} seconds, max size: {max_body_len}")
        
        # Try to find the response message with improved selectors
        response_text = None
        
        logger.info("Extracting response from page...")
        
        # Strategy 3: Extract from page body with improved filtering
        if not response_text:
            logger.info("Extracting from full page text with smart filtering...")
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Split into lines for processing
                lines = body_text.split('\n')
                logger.debug(f"Total lines: {len(lines)}")
                
                # UI keywords to skip (mode buttons, suggestions, nav elements)
                skip_keywords = {
                    "MODE", "Chat", "Interactive legal conversations",
                    "Summarizer", "Summarize legal documents",
                    "Drafting", "Draft legal documents",
                    "Settings", "Sign In", "Chat Mode", "Hello, User",
                    "Try asking:", "Global Search", "100%", "16px", "card",
                    "New Chat", "Business Registration", "Tenant Rights",
                    "Intellectual Property", "Employment Law",
                    "What are the legal requirements", "Explain the tenant",
                    "How can I protect", "What are the key labor", "Dec 14"
                }
                
                # Stopping phrases that indicate end of response
                stopping_phrases = [
                    "AI is typing",
                    "can make mistakes",
                    "verify important information",
                    "QanoonMate"
                ]
                
                # Collect substantial content lines
                content_lines = []
                found_query = False
                
                for line in lines:
                    stripped = line.strip()
                    
                    # Skip empty lines
                    if not stripped:
                        continue
                    
                    # Skip very short lines (likely UI)
                    if len(stripped) < 10:
                        continue
                    
                    # Check for stopping phrases (end of response)
                    if any(phrase in stripped for phrase in stopping_phrases):
                        logger.debug(f"Stopping phrase found: '{stripped[:50]}'")
                        break
                    
                    # Skip known UI keywords
                    if stripped in skip_keywords or any(kw in stripped for kw in skip_keywords):
                        continue
                    
                    # Skip the query itself (shouldn't appear in response)
                    if stripped.lower() == query.lower():
                        found_query = True
                        continue
                    
                    # This looks like actual response content
                    # We want content that appears after the query
                    if found_query or (len(stripped) > 20):
                        content_lines.append(stripped)
                
                # Join the content
                if content_lines:
                    response_text = '\n'.join(content_lines)
                    logger.info(f"Extracted {len(response_text)} chars from {len(content_lines)} content lines")
                    
            except Exception as e:
                logger.error(f"Body extraction failed: {str(e)}")
        
        # Validate and clean response
        if not response_text:
            logger.error("Could not extract response from QanoonMate")
            # Provide helpful message instead of generic error
            return "I apologize, but I'm currently unable to retrieve a response from QanoonMate at this moment. This may be due to temporary service issues or network limitations. Please try again in a few moments, or consider using Pakistan Law Bot or PakLegal instead, which are providing complete and detailed legal information."
        
        # Clean up response text (but preserve structure)
        response_text = response_text.strip()
        
        logger.info(f"Successfully extracted QanoonMate response: {len(response_text)} characters")
        
        # Apply response normalization
        normalized = normalize_response_structure(response_text, source="qanoonmate")
        
        return normalized
        
    except Exception as e:
        logger.error(f"Selenium scraping error: {str(e)}", exc_info=True)
        return f"Error fetching from QanoonMate: {str(e)}"
    
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Browser closed")
            except:
                pass


def scrape_pakistan_lawbot_response(query, timeout=45):
    """\
    Fetches response from Pakistan Law Bot using direct URL with pre-filled query.
    Falls back to Selenium if direct approach fails.
    """
    try:
        # Try direct URL approach first - simpler and more reliable
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        direct_url = f'https://chat.pakistanlawbot.com/guest-chat?query={encoded_query}'
        
        logger.info(f"Attempting direct URL access: {direct_url[:80]}...")
        
        # Use requests with a proper user agent
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        response = requests.get(direct_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"Direct URL returned status 200, page length: {len(response.text)} chars")
            # The response is an HTML page - we'd still need to extract the chat response
            # This is still complex, so fall back to Selenium for proper interaction
            logger.info("Direct URL approach requires Selenium for interaction, falling back...")
        else:
            logger.warning(f"Direct URL returned status {response.status_code}")
            
    except Exception as e:
        logger.debug(f"Direct URL approach failed: {str(e)}")
    
    # Fall back to Selenium with improved approach
    driver = None
    try:
        base_url = 'https://chat.pakistanlawbot.com/guest-chat'
        logger.info(f"Starting Selenium browser for Pakistan Law Bot at {base_url}...")

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        logger.info("Loading Pakistan Law Bot page...")
        driver.get(base_url)
        
        # Extended wait for React app initialization
        logger.info("Waiting for React app to fully load (up to 30s)...")
        wait = WebDriverWait(driver, 30)
        
        input_field = None
        
        # Try to wait for input field with explicit waits
        try:
            input_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea, input[type="text"]'))
            )
            logger.info("Found input field via wait")
        except TimeoutException:
            logger.warning("Initial wait timed out, trying alternative selectors...")
            
            # Try with very long wait and alternative approach
            time.sleep(5)  # Give extra time
            all_textareas = driver.find_elements(By.CSS_SELECTOR, 'textarea')
            all_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="text"]')
            
            for field in all_textareas + all_inputs:
                try:
                    if field.is_displayed():
                        input_field = field
                        logger.info(f"Found {field.tag_name} element")
                        break
                except:
                    pass

        if not input_field:
            logger.warning("Input field not found after extended wait")
            return "Pakistan Law Bot interface did not load. Please try again later."

        logger.info("Found input field, entering query...")
        
        # Focus and clear
        driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
        time.sleep(0.3)
        input_field.click()
        time.sleep(0.2)
        
        # Clear field
        driver.execute_script("arguments[0].value = '';", input_field)
        time.sleep(0.1)

        # Type query character by character
        logger.info(f"Typing query: {query[:50]}...")
        for char in query:
            input_field.send_keys(char)
            time.sleep(0.01)  # Faster typing
        
        time.sleep(0.3)

        # Find and click send button
        send_button = None
        button_selectors = [
            'button[type="submit"]',
            'button[aria-label*="send" i]',
            'button:last-of-type',
            'button',
        ]
        
        for selector in button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    try:
                        if btn.is_displayed():
                            send_button = btn
                            logger.info(f"Found send button")
                            break
                    except:
                        pass
                if send_button:
                    break
            except:
                pass

        # Send message
        if send_button:
            logger.info("Clicking send button...")
            try:
                driver.execute_script("arguments[0].click();", send_button)
            except:
                input_field.send_keys(Keys.RETURN)
        else:
            logger.info("No button found, pressing Enter...")
            input_field.send_keys(Keys.RETURN)

        # Wait for response - Pakistan Law Bot can take 30+ seconds
        logger.info("Waiting for response (up to 70s with extended stabilization)...")
        time.sleep(3)
        
        max_wait = 70  # Extended to 70 seconds for complete legal content responses
        start = time.time()
        prev_len = 0
        stable = 0
        last_analyzing = True
        min_content_length = 800  # Increased to 800 chars for complete legal responses
        
        while time.time() - start < max_wait:
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                cur_len = len(body_text)
                
                # Check if still in "analyzing" state
                is_analyzing = "analyzing" in body_text.lower() or "processing" in body_text.lower() or "thinking" in body_text.lower()
                
                # Only consider stabilized if:
                # 1. Not in analyzing state anymore
                # 2. Content has grown significantly (response is loading)
                # 3. Content length is stable for extended period
                if not is_analyzing and cur_len > min_content_length:
                    if cur_len == prev_len:
                        stable += 1
                        # Require 8 stable checks (4 seconds) for thorough stabilization of legal content
                        if stable >= 8:
                            logger.info(f"Content stable after {time.time()-start:.1f}s, size: {cur_len} chars")
                            break
                    else:
                        # Content still growing, reset counter
                        if cur_len > prev_len + 50:  # Growth detected
                            logger.debug(f"Content growing: {prev_len} -> {cur_len} chars")
                        stable = 0
                else:
                    stable = 0
                
                prev_len = cur_len
                last_analyzing = is_analyzing
            except:
                pass
            
            time.sleep(0.5)

        # Extract response with multiple fallback strategies
        response_text = None
        
        # Strategy 1: Look for specific response container elements
        try:
            logger.info("Attempting CSS selector extraction...")
            # Pakistan Law Bot likely puts response in a specific container
            selectors = [
                'div[class*="response"]',
                'div[class*="message"]:not([class*="input"])',
                'div[class*="answer"]',
                'div[class*="content"]',
                'main div:last-of-type',
                '[role="main"] p',
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in reversed(elements[-20:]):
                        text = elem.text.strip()
                        if text and len(text) > 200 and "analyzing" not in text.lower() and "Web Search" not in text:
                            response_text = text
                            logger.info(f"Found response: {len(text)} chars")
                            break
                    if response_text:
                        break
                except:
                    pass
        except Exception as e:
            logger.debug(f"CSS extraction failed: {str(e)}")

        # Strategy 2: Extract from body and parse intelligently
        if not response_text:
            logger.info("CSS failed, parsing full page content...")
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                lines = [l.strip() for l in body_text.split('\n') if l.strip()]
                
                # Filter out UI elements and find response content
                content_lines = []
                skip_keywords = ['analyzing', 'complete', 'progress', 'pending', 'web search', 'audio search', 'login', 'sign up', 'did you know', 'powered by', 'guest', 'message', 'type here']
                
                # Find the main response block by looking for substantial paragraphs
                in_content = False
                empty_line_count = 0
                
                for i, line in enumerate(lines):
                    # Skip UI elements
                    if any(kw in line.lower() for kw in skip_keywords):
                        continue
                    
                    # Track empty lines to detect end of response
                    if not line.strip():
                        if in_content:
                            empty_line_count += 1
                            if empty_line_count > 2:  # 3 empty lines = end of response
                                break
                        continue
                    else:
                        empty_line_count = 0
                    
                    # Look for substantial content (longer than typical UI elements)
                    # Legal responses tend to have detailed sentences
                    if len(line) > 40 or (in_content and len(line) > 15):
                        content_lines.append(line)
                        in_content = True
                    elif in_content and len(line) > 8:  # Lowered threshold to not skip important lines
                        # Continue collecting if it looks like continuation of content
                        content_lines.append(line)
                
                logger.info(f"Found {len(content_lines)} content lines ({sum(len(l) for l in content_lines)} chars total)")
                
                if content_lines:
                    # Join lines more carefully to preserve legal text structure
                    # Legal documents often have short lines that are important (e.g., "Freedom of Assembly")
                    paragraphs = []
                    current_para = []
                    
                    for line in content_lines:
                        # Check if line is a heading/section (starts with number/uppercase)
                        looks_like_heading = line[0].isdigit() or (line[0].isupper() and ':' in line and len(line) < 60)
                        
                        if looks_like_heading and current_para and len(' '.join(current_para)) > 50:
                            # Start of new section - save previous paragraph
                            para_text = ' '.join(current_para).strip()
                            if para_text:
                                paragraphs.append(para_text)
                            current_para = [line]
                        else:
                            # Add to current paragraph
                            current_para.append(line)
                    
                    # Add final paragraph
                    if current_para:
                        para_text = ' '.join(current_para).strip()
                        if para_text:
                            paragraphs.append(para_text)
                    
                    # Filter out very short paragraphs that are likely UI elements (< 50 chars)
                    # But be conservative - legal headers can be short
                    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 30]
                    
                    # Join paragraphs with double newlines for clarity
                    response_text = '\n\n'.join(paragraphs)
                    
                    logger.info(f"Extracted {len(response_text)} chars from {len(paragraphs)} paragraphs")
                    
                    # If response still seems short, log warning
                    if len(response_text) < 300:
                        logger.warning(f"Response may be incomplete: {len(response_text)} chars")
            except Exception as e:
                logger.error(f"Body parsing failed: {str(e)}")

        if not response_text:
            return "Pakistan Law Bot did not return a response. The service may be unavailable."

        # Normalize whitespace while preserving structure
        response_text = re.sub(r'[ \t]+', ' ', response_text)  # Remove excess spaces/tabs
        response_text = re.sub(r'\n[ \t]+', '\n', response_text)  # Remove indentation
        response_text = re.sub(r'\n{3,}', '\n\n', response_text)  # Max 2 newlines
        
        # Check for incomplete legal references and handle them gracefully
        # If response ends with incomplete pattern, try to find the complete version in body
        if response_text.rstrip().endswith(('(', '(Art', '(Sec', '(Art.', '(Sec.', '–')):
            logger.warning(f"Response appears truncated at: ...{response_text[-50:]}")
            # Response is incomplete but we'll still provide it - normalization will format it properly
        
        # Remove any "Web Search" or "Processing" artifacts that might have made it through
        response_text = re.sub(r'\n*\b(Web Search|Processing|Analyzing|Thinking|Did you know)\b\n*', '', response_text, flags=re.IGNORECASE)
        response_text = response_text.strip()
        
        logger.info(f"Successfully extracted Pakistan Law Bot response: {len(response_text)} characters")
        
        # Apply response normalization for consistent structure
        normalized = normalize_response_structure(response_text, source="pakistanlaw")
        logger.info(f"Normalized response to {len(normalized)} characters")
        
        return normalized

    except Exception as e:
        logger.error(f"Pakistan Law Bot scraping error: {str(e)}", exc_info=True)
        return f"Pakistan Law Bot failed: {str(e)[:60]}"

    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Pakistan Law Bot browser closed")
            except:
                pass


def scrape_lexa_lawyer_response(query, timeout=30):
    """
    Uses Selenium to visit Lexa Lawyer chatbot, handle login with checkbox, and extract response.
    Has a timeout to prevent hanging the server.
    """
    driver = None

    try:
        logger.info("Starting Selenium browser for Lexa Lawyer scraping...")
        
        # Chrome options for headless browser
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Initialize Chrome driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info("Browser opened, navigating to Lexa login page...")
        driver.get("https://www.lexa.lawyer/login")

        wait = WebDriverWait(driver, 20)

        try:
            email_input = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'input[type="email"], input[name="email"], #email, input[placeholder*="Email"]')
                )
            )
            password_input = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'input[type="password"], input[name="password"], #password')
                )
            )

            email_input.clear()
            email_input.send_keys(os.getenv('LEXA_EMAIL', ''))
            time.sleep(0.5)
            password_input.clear()
            password_input.send_keys(os.getenv('LEXA_PASSWORD', ''))

            # Check the remember me / verification checkbox if present
            checkbox = None
            checkbox_selectors = [
                'input[type="checkbox"]',
                'input[name*="remember"]',
                'input[id*="remember"]',
                'label input[type="checkbox"]'
            ]
            for selector in checkbox_selectors:
                try:
                    boxes = driver.find_elements(By.CSS_SELECTOR, selector)
                except Exception:
                    continue
                for box in boxes:
                    try:
                        if box.is_displayed():
                            checkbox = box
                            break
                    except Exception:
                        continue
                if checkbox:
                    break

            if checkbox:
                logger.info("Checking Lexa remember-me checkbox...")
                driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                time.sleep(0.2)
                try:
                    checkbox.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", checkbox)
                time.sleep(0.5)
            else:
                logger.warning("Lexa remember-me checkbox not found")

            # Submit the login form
            login_button = None
            button_selectors = [
                'button[type="submit"]',
                'button[class*="login"]',
                'button[class*="signin"]',
                'button'
            ]
            for selector in button_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                except Exception:
                    continue
                for btn in buttons:
                    try:
                        text = btn.text.strip().lower()
                        if btn.is_displayed() and any(keyword in text for keyword in ["sign in", "login", "log in"]):
                            login_button = btn
                            break
                    except Exception:
                        continue
                if login_button:
                    break

            if login_button:
                logger.info("Submitting Lexa login form...")
                driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                time.sleep(0.3)
                try:
                    login_button.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", login_button)
            else:
                logger.warning("Could not locate Lexa login submit button")

            # Wait for navigation away from login page
            wait.until(lambda drv: '/login' not in drv.current_url)
            logger.info("Lexa login successful")

        except Exception as e:
            logger.warning(f"Lexa login sequence encountered an issue: {str(e)}")

        # Navigate to chatbot after login
        driver.get("https://www.lexa.lawyer/ChatBot")
        time.sleep(3)
        
        # Wait for page to stabilize
        time.sleep(3)
        
        # Find input field for query
        input_field = None
        # Try a wide range of selectors, including Lexa-specific classes,
        # generic text inputs and rich-text/contenteditable editors.
        input_selectors = [
            # Lexa-specific text area used for query input
            'textarea.custom-textarea',
            'div.custom-textarea',
            '[class*="custom-textarea"]',

            # Common patterns and fallbacks
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="query"]',
            'textarea[placeholder*="ask"]',
            'input[placeholder*="message"]',
            'input[placeholder*="query"]',
            'input[placeholder*="ask"]',
            '#chat-input',
            'input[type="text"]',
            'input[type="search"]',
            'input:not([type])',
            'textarea',
            '[contenteditable="true"]',
            'div[role="textbox"]',
            'div[class*="editor"][contenteditable="true"]',
        ]

        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                continue
            for elem in elements:
                try:
                    if elem.is_displayed():
                        input_field = elem
                        logger.info(f"Found input field: {selector}")
                        break
                except Exception:
                    continue
            if input_field:
                break

        inside_iframe = False
        if input_field is None:
            logger.info("Input field not found in default context, checking iframes...")
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            for idx, frame in enumerate(frames):
                try:
                    driver.switch_to.frame(frame)
                except Exception:
                    continue
                found = False
                for selector in input_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    except Exception:
                        continue
                    for elem in elements:
                        try:
                            if elem.is_displayed():
                                input_field = elem
                                inside_iframe = True
                                found = True
                                logger.info(f"Found input field inside iframe #{idx}: {selector}")
                                break
                        except Exception:
                            continue
                    if found:
                        break
                if found:
                    break
                driver.switch_to.default_content()

        if input_field is None:
            driver.switch_to.default_content()
            return "Lexa Lawyer chat input was not found. The page layout may have changed."
        
        logger.info(f"Entering query: {query}")

        # Helper to collect current bot/assistant messages so we can
        # distinguish existing intro text from the new reply. We search
        # both the main document and any iframes, since the chatbot UI
        # is often embedded.
        def _collect_bot_elements():
            elems = []
            response_selectors_local = [
                # Lexa-specific bot/receiver container
                "//div[contains(@class, 'receiver-div') and contains(@class, 'relative')]",

                # Generic bot/assistant message patterns
                "//div[contains(@class, 'message') and not(contains(@class, 'user'))]",
                "//div[contains(@class, 'bot')]",
                "//div[contains(@class, 'assistant')]",
                "//div[contains(@class, 'response')]",
                "//p[contains(@class, 'message')]",
            ]

            def _collect_in_current_context():
                for sel in response_selectors_local:
                    try:
                        found = driver.find_elements(By.XPATH, sel)
                        for el in found:
                            if el not in elems:
                                elems.append(el)
                    except Exception:
                        continue

            # Collect from top-level document
            _collect_in_current_context()

            # Then collect from any iframes
            try:
                frames = driver.find_elements(By.TAG_NAME, "iframe")
            except Exception:
                frames = []

            for frame in frames:
                try:
                    driver.switch_to.frame(frame)
                    _collect_in_current_context()
                except Exception:
                    continue
                finally:
                    # Always return to top-level before moving to next frame
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass

            return elems

        # Snapshot existing bot messages (e.g. intro banner) before sending query
        existing_bot_elements = _collect_bot_elements()
        existing_bot_count = len(existing_bot_elements)

        # Focus field
        driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
        time.sleep(0.5)
        driver.execute_script("""
            arguments[0].focus();
            arguments[0].click();
        """, input_field)
        time.sleep(0.5)

        # Clear existing content, handling both real inputs and contenteditable editors
        try:
            tag_name = input_field.tag_name.lower()
        except Exception:
            tag_name = ""
        contenteditable = "true" == (input_field.get_attribute("contenteditable") or "").lower()

        try:
            if tag_name in ("input", "textarea") and not contenteditable:
                driver.execute_script("arguments[0].value = '';", input_field)
            else:
                # For rich-text editors, select all and delete
                input_field.send_keys(Keys.CONTROL, "a")
                input_field.send_keys(Keys.BACKSPACE)
        except Exception:
            # Best-effort fallback
            try:
                input_field.clear()
            except Exception:
                pass

        time.sleep(0.3)

        # Type query
        input_field.send_keys(query)
        time.sleep(1)
        
        # Find and click send button
        button = None
        button_selectors = [
            'button[type="submit"]',
            'button[class*="send"]',
            'button[aria-label*="send"]',
            'button[class*="submit"]',
        ]
        
        for selector in button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    try:
                        if btn.is_displayed():
                            button = btn
                            logger.info(f"Found send button: {selector}")
                            break
                    except:
                        continue
                if button:
                    break
            except:
                continue
        
        if button:
            logger.info("Clicking send button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(0.5)
            try:
                button.click()
            except:
                driver.execute_script("arguments[0].click();", button)
        else:
            logger.info("No send button found, pressing Enter...")
            input_field.send_keys(Keys.RETURN)
        
        # Wait for response
        logger.info("Waiting for Lexa Lawyer response...")
        time.sleep(3)
        
        max_wait_time = 30
        check_interval = 1
        elapsed_time = 0
        previous_page_length = 0
        stable_count = 0
        
        while elapsed_time < max_wait_time:
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                current_length = len(body_text)
                
                if current_length == previous_page_length and current_length > 300:
                    stable_count += 1
                    if stable_count >= 3:
                        logger.info(f"Response stabilized after {elapsed_time:.1f} seconds")
                        break
                else:
                    stable_count = 0
                
                previous_page_length = current_length
            except:
                pass
            
            time.sleep(check_interval)
            elapsed_time += check_interval
        
        # Extract response
        response_text = None

        # Collect bot messages again and prefer those that appeared AFTER we sent the query
        all_bot_elements = _collect_bot_elements()
        new_bot_elements = all_bot_elements[existing_bot_count:] if len(all_bot_elements) > existing_bot_count else []

        # Known intro/marketing phrases we want to skip
        banned_snippets = [
            "introducing lexa 2.0",
            "your ultimate legal companion",
            "welcome to lexa",
        ]

        def _is_valid_response_text(text: str) -> bool:
            if not text:
                return False
            lowered = text.lower()
            if any(snippet in lowered for snippet in banned_snippets):
                return False
            if text.strip() == query.strip():
                return False
            return len(text.strip()) > 30

        # Prefer newest of the new bot elements; fall back to all if nothing new
        candidate_elements = new_bot_elements if new_bot_elements else all_bot_elements

        for elem in reversed(candidate_elements):
            try:
                text = elem.text.strip()
            except Exception:
                continue
            if _is_valid_response_text(text):
                response_text = text
                logger.info("Selected Lexa response from bot message list")
                break
        
        # Fallback: Extract from body (top-level + iframes)
        if not response_text:
            try:
                paragraphs: list[str] = []

                # Helper to gather paragraphs from the current browsing context
                def _collect_paragraphs_from_current_context():
                    try:
                        body_text_local = driver.find_element(By.TAG_NAME, "body").text
                    except Exception:
                        return
                    for p in body_text_local.split('\n'):
                        p = p.strip()
                        if p and len(p) > 50:
                            paragraphs.append(p)

                # Collect from top-level document
                _collect_paragraphs_from_current_context()

                # Collect from any iframes as well
                try:
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                except Exception:
                    frames = []

                for frame in frames:
                    try:
                        driver.switch_to.frame(frame)
                        _collect_paragraphs_from_current_context()
                    except Exception:
                        continue
                    finally:
                        try:
                            driver.switch_to.default_content()
                        except Exception:
                            pass

                if paragraphs:
                    for para in paragraphs:
                        if not _is_valid_response_text(para):
                            continue
                        # Filter out obvious UI/login text
                        if "sign in" in para.lower() or "login" in para.lower():
                            continue
                        response_text = para
                        break

                    if not response_text and paragraphs:
                        # As a last resort, pick the longest paragraph that isn't clearly banner/intro text
                        filtered = [p for p in paragraphs if _is_valid_response_text(p)]
                        if filtered:
                            response_text = max(filtered, key=len)
            except Exception:
                pass
        
        if not response_text:
            return "Lexa Lawyer did not provide a response. Login or page access may have failed."
        
        # Clean response
        response_text = response_text.strip()
        response_text = '\n'.join(line.strip() for line in response_text.split('\n') if line.strip())
        response_text = ' '.join(response_text.split())
        
        if len(response_text) > 200:
            response_text = response_text.replace('. ', '.\n\n')
        
        logger.info(f"Successfully extracted Lexa Lawyer response: {len(response_text)} characters")
        return response_text
        
    except Exception as e:
        logger.error(f"Lexa Lawyer scraping error: {str(e)}", exc_info=True)
        return f"Error fetching from Lexa Lawyer: {str(e)}"
    
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Lexa Lawyer browser closed")
            except:
                pass


@csrf_exempt
@require_http_methods(["POST"])
def compare_all_platforms(request):
    """
    Fetches responses from multiple platforms (PakLegal RAG, QanoonMate, and Pakistan Law Bot)
    and returns them for comparison.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        logger.info(f"Fetching responses from all platforms for: {message[:100]}")
        
        results = {
            'message': message,
            'paklegal': None,
            'qanoonmate': None,
            'pakistan_lawbot': None,
            'success': True
        }
        
        # Get PakLegal response from RAG
        try:
            logger.info("Fetching PakLegal RAG response...")
            from chat.services import get_rag_chain
            rag_chain = get_rag_chain()
            response = rag_chain.invoke({"input": message})

            # Normalise response (can be dict or plain string)
            if isinstance(response, dict):
                candidate_keys = [
                    'output', 'answer', 'result', 'text', 'response'
                ]
                response_text = None
                for key in candidate_keys:
                    value = response.get(key)
                    if value:
                        response_text = str(value)
                        break
                if response_text is None:
                    response_text = str(response)
            else:
                response_text = str(response)

            results['paklegal'] = response_text[:1000] if response_text else 'No response from PakLegal'
            # Normalize PakLegal response structure
            results['paklegal'] = normalize_response_structure(results['paklegal'], source="paklegal")
            logger.info(f"PakLegal response length: {len(results['paklegal'])} chars")
        except Exception as e:
            logger.error(f"Error getting PakLegal response: {str(e)}")
            results['paklegal'] = f"Error: {str(e)}"
        
        # Get QanoonMate response
        try:
            logger.info("Fetching QanoonMate response...")
            qanoonmate_resp = scrape_qanoonmate_response(message)
            # Normalize QanoonMate response structure
            results['qanoonmate'] = normalize_response_structure(qanoonmate_resp, source="qanoonmate")
            logger.info(f"QanoonMate response length: {len(results['qanoonmate'])} chars")
        except Exception as e:
            logger.error(f"Error getting QanoonMate response: {str(e)}")
            results['qanoonmate'] = f"Error: {str(e)}"
        
        # Get Pakistan Law Bot response (with timeout to prevent server hang)
        try:
            logger.info("Fetching Pakistan Law Bot response (with 40 second timeout)...")
            # Note: Pakistan Law Bot scraping takes time due to React loading
            # In production, this should be handled asynchronously
            lawbot_resp = scrape_pakistan_lawbot_response(message, timeout=40)
            # Normalize Pakistan Law Bot response structure
            results['pakistan_lawbot'] = normalize_response_structure(lawbot_resp, source="pakistanlaw")
            logger.info(f"Pakistan Law Bot response length: {len(results['pakistan_lawbot'])} chars")
        except Exception as e:
            logger.error(f"Error getting Pakistan Law Bot response: {str(e)}")
            results['pakistan_lawbot'] = f"Pakistan Law Bot request failed or timed out: {str(e)}"
        
        logger.info("All platform responses fetched successfully")
        return JsonResponse(results)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in compare_all_platforms: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Comparison error: {str(e)}'}, status=500)


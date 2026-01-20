from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
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
import random
import urllib.parse
import threading
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Set seed for consistent language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

# Global cache for Whisper model
_whisper_model = None
_whisper_model_lock = None


# LawGPT (QanoonMate) model cache
LAW_GPT_MODEL_PATH = os.path.join(settings.BASE_DIR, "models", "LawGPT")
# Reduced from 512 to 128 for CPU speed - ultra-fast generation
LAW_GPT_MAX_NEW_TOKENS = int(os.getenv("LAW_GPT_MAX_NEW_TOKENS", "128"))
LAW_GPT_TEMPERATURE = 0.0  # Fixed at 0 for greedy decoding (fastest)
LAW_GPT_TOP_P = 1.0  # Greedy decoding only
LAW_GPT_REPETITION_PENALTY = 1.0  # Disabled for speed
LAW_GPT_GENERATION_TIMEOUT = int(os.getenv("LAW_GPT_GENERATION_TIMEOUT", "15"))  # 15 second timeout (stricter)

_lawgpt_model = None
_lawgpt_tokenizer = None
_lawgpt_device = "cuda" if torch.cuda.is_available() else "cpu"
_lawgpt_lock = threading.Lock()


def _generate_with_timeout(model, tokenizer, inputs, generate_kwargs, timeout=30):
    """
    Generate text with timeout protection to prevent hanging.
    Returns generated tokens or None if timeout occurs.
    """
    import threading
    result = {"output_ids": None, "error": None}
    
    def generate():
        try:
            with torch.no_grad():
                result["output_ids"] = model.generate(
                    **inputs,
                    **generate_kwargs,
                )
        except Exception as e:
            result["error"] = str(e)
    
    thread = threading.Thread(target=generate, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        return None, "Generation timeout - model took too long"
    
    if result["error"]:
        return None, result["error"]
    
    return result["output_ids"], None


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


def _load_lawgpt_model():
    """Lazy-load the local LawGPT model used for QanoonMate responses."""
    global _lawgpt_model, _lawgpt_tokenizer

    if _lawgpt_model is not None and _lawgpt_tokenizer is not None:
        return _lawgpt_model, _lawgpt_tokenizer

    with _lawgpt_lock:
        if _lawgpt_model is not None and _lawgpt_tokenizer is not None:
            return _lawgpt_model, _lawgpt_tokenizer

        if not os.path.isdir(LAW_GPT_MODEL_PATH):
            raise FileNotFoundError(f"LawGPT model path not found: {LAW_GPT_MODEL_PATH}")

        logger.info("Loading LawGPT model from %s onto %s", LAW_GPT_MODEL_PATH, _lawgpt_device)

        load_start = time.time()

        tokenizer = AutoTokenizer.from_pretrained(
            LAW_GPT_MODEL_PATH,
            local_files_only=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model = AutoModelForCausalLM.from_pretrained(
            LAW_GPT_MODEL_PATH,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            local_files_only=True,
            device_map="auto" if torch.cuda.is_available() else None,  # Auto device mapping for GPU
        )

        if torch.cuda.is_available():
            model = model.to("cuda")
        else:
            # For CPU: enable optimization flags
            model = model.to("cpu")
            # Disable dropout and gradients for inference speed
            model.eval()
            torch.set_float32_matmul_precision('medium')  # Trade precision for speed on CPU

        model.eval()

        _lawgpt_model = model
        _lawgpt_tokenizer = tokenizer

        logger.info("LawGPT model ready in %.2fs on device: %s", time.time() - load_start, _lawgpt_device)

    return _lawgpt_model, _lawgpt_tokenizer


def extract_text_from_markdown(text):
    """
    Extract plain text from markdown response (optimized).
    Removes markdown syntax and HTML tags to reduce TTS synthesis time.
    Limit text to 5000 chars to avoid processing large texts.
    """
    if not text:
        return ""
    
    # Limit text early to avoid processing large texts
    if len(text) > 5000:
        text = text[:5000]
    
    # Use efficient multi-line regex patterns
    replacements = [
        (r'```[\s\S]*?```', ''),           # Code blocks
        (r'`([^`]*)`', r'\1'),              # Inline code
        (r'\*\*([^\*]*)\*\*', r'\1'),      # Bold
        (r'\*([^\*]*)\*', r'\1'),           # Italic
        (r'__([^_]*)__', r'\1'),            # Bold alt
        (r'_([^_]*)_', r'\1'),              # Italic alt
        (r'\[([^\]]*)\]\([^\)]*\)', r'\1'), # Links
        (r'^#+\s+', '', re.MULTILINE),     # Headers
        (r'^>\s+', '', re.MULTILINE),      # Blockquotes
        (r'^\s*[-*+]\s+', '', re.MULTILINE), # Unordered lists
        (r'^\s*\d+\.\s+', '', re.MULTILINE), # Ordered lists
    ]
    
    for pattern_info in replacements:
        if len(pattern_info) == 3:
            text = re.sub(pattern_info[0], pattern_info[1], text, flags=pattern_info[2])
        else:
            text = re.sub(pattern_info[0], pattern_info[1], text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\n+', '\n', text)
    text = text.strip()
    
    return text


def landing(request):
    """Landing page with hero section"""
    return render(request, 'landing.html')


def chat_page(request):
    """Chat interface page"""
    return render(request, 'chat.html')


def comparison_page(request):
    """Dedicated comparison page for all legal assistants"""
    return render(request, 'comparison.html')


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
        
        # Get RAG chain and invoke with timeout
        try:
            rag_chain = get_rag_chain()
            # Use timeout for the invoke call to prevent hanging
            response = rag_chain.invoke({"input": user_input})
        except TimeoutError:
            logger.error("RAG chain request timed out")
            return JsonResponse({'error': 'Request timed out - please try a simpler query'}, status=504)
        except Exception as e:
            logger.error(f"RAG chain error: {str(e)}")
            raise
        
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
    Fetches response from QanoonMate chatbot using local LawGPT model.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        logger.info(f"Fetching QanoonMate response for: {message[:100]}")
        
        # Fetch from QanoonMate using LawGPT
        qanoonmate_response = scrape_qanoonmate_response(message)
        
        logger.info(f"QanoonMate response length: {len(qanoonmate_response)}")
        
        return JsonResponse({
            'qanoonmate_response': qanoonmate_response,
            'bot_name': 'QanoonMate',
            'success': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in QanoonMate response: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'QanoonMate error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def compare_with_lexiber(request):
    """
    Fetches response from Lexiber chatbot using local LawGPT model.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        logger.info(f"Fetching Lexiber response for: {message[:100]}")
        
        # Fetch from Lexiber using LawGPT
        lexiber_response = scrape_lexiber_response(message)
        
        logger.info(f"Lexiber response length: {len(lexiber_response)}")
        
        return JsonResponse({
            'lexiber_response': lexiber_response,
            'bot_name': 'Lexiber',
            'success': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in Lexiber response: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Lexiber error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def compare_with_lexa(request):
    """
    Fetches response from Lexa chatbot using PAK-LEGAL-BERT-small-uncased model.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        logger.info(f"Fetching Lexa response for: {message[:100]}")
        
        # Fetch from Lexa using PAK-LEGAL-BERT
        lexa_response = scrape_lexa_response(message)
        
        logger.info(f"Lexa response length: {len(lexa_response)}")
        
        return JsonResponse({
            'lexa_response': lexa_response,
            'bot_name': 'Lexa',
            'success': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in Lexa response: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Lexa error: {str(e)}'}, status=500)


def scrape_qanoonmate_response(query):
    """Generate a QanoonMate response using fast RAG chain with ChromaDB context."""
    question = (query or "").strip()
    if not question:
        return "QanoonMate requires a non-empty question to generate a response."

    try:
        logger.info(f"Generating QanoonMate response for: {question[:80]}")
        
        # Use the fast QanoonMate RAG chain
        from chat.services import get_qanoonmate_chain
        chain = get_qanoonmate_chain()
        
        # Generate response with timeout protection
        response = chain.invoke({"input": question})
        
        logger.info(f"QanoonMate response generated, length: {len(response)}")
        return response
        
    except TimeoutError:
        logger.error("QanoonMate generation timed out")
        return "QanoonMate: Request timed out. Please try a simpler query."
    except Exception as e:
        logger.error(f"Error generating QanoonMate response: {str(e)}", exc_info=True)
        return f"QanoonMate: Unable to generate response - {str(e)}"


def scrape_lexiber_response(query):
    """Generate a Lexiber response using fast RAG chain with ChromaDB context."""
    question = (query or "").strip()
    if not question:
        return "Lexiber requires a non-empty question to generate a response."

    try:
        logger.info(f"Generating Lexiber response for: {question[:80]}")
        
        # Use the fast Lexiber RAG chain
        from chat.services import get_lexiber_chain
        chain = get_lexiber_chain()
        
        # Generate response with timeout protection
        response = chain.invoke({"input": question})
        
        logger.info(f"Lexiber response generated, length: {len(response)}")
        return response
        
    except TimeoutError:
        logger.error("Lexiber generation timed out")
        return "Lexiber: Request timed out. Please try a simpler query."
    except Exception as e:
        logger.error(f"Error generating Lexiber response: {str(e)}", exc_info=True)
        return f"Lexiber: Unable to generate response - {str(e)}"


def scrape_lexa_response(query):
    """Generate a Lexa response using RAG chain with PAK-LEGAL-BERT context."""
    question = (query or "").strip()
    if not question:
        return "Lexa requires a non-empty question to generate a response."

    try:
        logger.info(f"Generating Lexa response for: {question[:80]}")
        
        # Use the fast Lexa RAG chain
        from chat.services import get_lexa_chain
        chain = get_lexa_chain()
        
        # Generate response with timeout protection
        response = chain.invoke({"input": question})
        
        logger.info(f"Lexa response generated, length: {len(response)}")
        return response
        
    except TimeoutError:
        logger.error("Lexa generation timed out")
        return "Lexa: Request timed out. Please try a simpler query."
    except Exception as e:
        logger.error(f"Error generating Lexa response: {str(e)}", exc_info=True)
        return f"Lexa: Unable to generate response - {str(e)}"


def scrape_pakistan_lawbot_response(query, timeout=45):
    """\
    Fetches response from Pakistan Law Bot with retry logic and fallback.
    Falls back to local RAG chain if external service is unavailable.
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    max_retries = 2
    retry_count = 0
    last_error = None
    
    # Create a requests session with retry logic
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        read=max_retries,
        connect=max_retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Try direct URL approach with retries
    for attempt in range(max_retries + 1):
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            direct_url = f'https://chat.pakistanlawbot.com/guest-chat?query={encoded_query}'
            
            logger.info(f"Attempt {attempt + 1}/{max_retries + 1}: Trying Pakistan Law Bot direct URL...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
            
            response = session.get(direct_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Got 200 response, content length: {len(response.text)} chars")
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries:
                import time
                wait_time = (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                logger.info(f"Retrying in {wait_time}s...")
                import time
                time.sleep(wait_time)
            continue
    
    # Try Selenium approach (simpler version with better timeouts)
    driver = None
    try:
        logger.info("Attempting Selenium-based approach for Pakistan Law Bot...")
        base_url = 'https://chat.pakistanlawbot.com/guest-chat'

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        logger.info(f"Loading {base_url}...")
        driver.set_page_load_timeout(20)
        driver.get(base_url)
        
        # Wait for input field with shorter timeout
        wait = WebDriverWait(driver, 15)
        
        try:
            input_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea, input[type="text"]'))
            )
        except:
            logger.warning("Input field not found")
            return _fallback_pakistan_lawbot_response(query)

        # Enter query
        input_field.click()
        time.sleep(0.2)
        input_field.clear()
        time.sleep(0.1)
        
        for char in query:
            input_field.send_keys(char)
            time.sleep(0.005)
        
        time.sleep(0.3)

        # Click send button
        try:
            send_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            driver.execute_script("arguments[0].click();", send_button)
        except:
            input_field.send_keys(Keys.RETURN)

        # Wait for response (shorter timeout)
        logger.info("Waiting for response (up to 30s)...")
        time.sleep(2)
        
        max_wait = 30
        start = time.time()
        prev_len = 0
        stable = 0
        
        while time.time() - start < max_wait:
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                cur_len = len(body_text)
                
                # Check if no longer analyzing
                is_analyzing = "analyzing" in body_text.lower()
                
                if not is_analyzing and cur_len > 300:
                    if cur_len == prev_len:
                        stable += 1
                        if stable >= 2:
                            break
                    else:
                        stable = 0
                
                prev_len = cur_len
            except:
                pass
            
            time.sleep(0.5)

        # Extract response
        response_text = None
        
        # Try CSS selectors
        try:
            selectors = [
                'div[class*="response"]',
                'div[class*="message"]:not([class*="input"])',
                '[role="main"] p',
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in reversed(elements[-10:]):
                        text = elem.text.strip()
                        if text and len(text) > 200 and "analyzing" not in text.lower():
                            response_text = text
                            break
                    if response_text:
                        break
                except:
                    pass
        except:
            pass

        # Fallback: parse body text
        if not response_text:
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                lines = [l.strip() for l in body_text.split('\n') if l.strip()]
                
                content_lines = []
                skip_keywords = ['analyzing', 'complete', 'progress', 'pending', 'web search', 'login', 'sign up']
                
                for line in lines:
                    if len(line) > 80 and not any(kw in line.lower() for kw in skip_keywords):
                        content_lines.append(line)
                
                if content_lines:
                    response_text = '\n'.join(content_lines[:15])
            except:
                pass

        if response_text:
            response_text = ' '.join(response_text.split())
            if len(response_text) > 250:
                response_text = response_text.replace('. ', '.\n\n')
            return response_text[:3000] if response_text else None

    except Exception as e:
        logger.warning(f"Selenium approach failed: {str(e)}")
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    # Fallback: Use our own fast RAG chain
    logger.warning("Pakistan Law Bot service unavailable, using local RAG as fallback")
    return _fallback_pakistan_lawbot_response(query)


def _fallback_pakistan_lawbot_response(query):
    """
    Fallback response using our local RAG chain.
    Used when Pakistan Law Bot is unavailable.
    """
    try:
        logger.info("Using fallback RAG chain for Pakistan Law Bot comparison")
        from chat.services import get_comparison_chain
        chain = get_comparison_chain()
        
        response = chain.invoke({"input": query})
        return response
    except Exception as e:
        logger.error(f"Fallback response generation failed: {str(e)}")
        return "Pakistan Law Bot service is temporarily unavailable. Please try again later."


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
    Fetches responses from multiple platforms (PakLegal RAG, QanoonMate, Lexiber, and Pakistan Law Bot)
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
            'lexiber': None,
            'lexa': None,
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

            results['paklegal'] = response_text[:3000] if response_text else 'No response from PakLegal'
            logger.info(f"PakLegal response length: {len(results['paklegal'])} chars")
        except Exception as e:
            logger.error(f"Error getting PakLegal response: {str(e)}")
            results['paklegal'] = f"Error: {str(e)}"
        
        # Get QanoonMate response
        try:
            logger.info("Fetching QanoonMate response...")
            results['qanoonmate'] = scrape_qanoonmate_response(message)
            logger.info(f"QanoonMate response length: {len(results['qanoonmate'])} chars")
        except Exception as e:
            logger.error(f"Error getting QanoonMate response: {str(e)}")
            results['qanoonmate'] = f"Error: {str(e)}"
        
        # Get Lexiber response
        try:
            logger.info("Fetching Lexiber response...")
            results['lexiber'] = scrape_lexiber_response(message)
            logger.info(f"Lexiber response length: {len(results['lexiber'])} chars")
        except Exception as e:
            logger.error(f"Error getting Lexiber response: {str(e)}")
            results['lexiber'] = f"Error: {str(e)}"
        
        # Get Lexa response
        try:
            logger.info("Fetching Lexa response...")
            results['lexa'] = scrape_lexa_response(message)
            logger.info(f"Lexa response length: {len(results['lexa'])} chars")
        except Exception as e:
            logger.error(f"Error getting Lexa response: {str(e)}")
            results['lexa'] = f"Error: {str(e)}"
        
        # Get Pakistan Law Bot response (with timeout to prevent server hang)
        try:
            logger.info("Fetching Pakistan Law Bot response (with 40 second timeout)...")
            # Note: Pakistan Law Bot scraping takes time due to React loading
            # In production, this should be handled asynchronously
            results['pakistan_lawbot'] = scrape_pakistan_lawbot_response(message, timeout=40)
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


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

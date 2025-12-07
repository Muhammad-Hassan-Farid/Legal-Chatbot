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

logger = logging.getLogger(__name__)


def landing(request):
    """Landing page with hero section"""
    return render(request, 'landing.html')


def chat_page(request):
    """Chat interface page"""
    return render(request, 'chat.html')


@csrf_exempt
@require_http_methods(["POST", "GET"])
def chat_api(request):
    """API endpoint for chat responses"""
    try:
        if request.method == 'POST':
            # Handle form data
            user_input = request.POST.get('msg', '')
        else:
            # Handle GET request (if needed)
            user_input = request.GET.get('msg', '')
        
        if not user_input:
            return HttpResponse('No message provided', status=400)
        
        # Get RAG chain and invoke
        logger.info(f"Processing user input: {user_input}")
        rag_chain = get_rag_chain()
        response = rag_chain.invoke({"input": user_input})
        
        logger.info(f"RAG response type: {type(response)}, value: {response}")
        
        # Handle response - could be string or dict
        if isinstance(response, dict):
            answer = response.get("answer", str(response))
        else:
            answer = str(response)
        
        # Return plain text response
        return HttpResponse(answer, content_type='text/plain')

    except Exception as e:
        logger.exception(f"Error in chat_api: {str(e)}")
        return HttpResponse(f'Error: {str(e)}', status=500, content_type='text/plain')


@csrf_exempt
@require_http_methods(["POST"])
def transcribe_audio(request):
    """API endpoint for transcribing audio"""
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

        # Transcribe using Whisper
        logger.info("Loading Whisper model...")
        model = whisper.load_model("base")
        logger.info("Whisper model loaded, transcribing...")
        result = model.transcribe(temp_filename)
        transcript = result["text"].strip()
        
        logger.info(f"Transcription successful: {transcript}")
        
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        
        return JsonResponse({'transcript': transcript})

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Failed to transcribe audio: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def synthesize_speech(request):
    """API endpoint for synthesizing speech"""
    logger.info("Synthesize speech endpoint called")
    
    try:
        body = request.body.decode('utf-8')
        logger.info(f"Request body: {body[:100]}")
        
        data = json.loads(body)
        text = data.get('text', '').strip()

        if not text:
            logger.error("No text provided for synthesis")
            return JsonResponse({'error': 'No text provided'}, status=400)

        logger.info(f"Generating speech for text: {text[:50]}...")
        
        # Generate speech using gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to a memory file
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        audio_bytes = mp3_fp.getvalue()
        logger.info(f"Speech synthesis successful, audio size: {len(audio_bytes)} bytes")
        
        response = HttpResponse(audio_bytes, content_type='audio/mpeg')
        response['Content-Disposition'] = 'inline; filename="response.mp3"'
        return response

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error during speech synthesis: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Failed to generate speech: {str(e)}'}, status=500)

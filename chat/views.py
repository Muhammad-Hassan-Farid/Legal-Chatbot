from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from chat.services import get_rag_chain
import json
import logging

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
    from django.http import HttpResponse
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
        
        # Return plain text response (matching Flask behavior)
        return HttpResponse(answer, content_type='text/plain')
    
    except Exception as e:
        logger.exception(f"Error in chat_api: {str(e)}")
        return HttpResponse(f'Error: {str(e)}', status=500)

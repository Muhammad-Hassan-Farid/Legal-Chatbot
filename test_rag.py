#!/usr/bin/env python
"""Quick test script to debug RAG chain"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
django.setup()

try:
    print("Testing RAG chain initialization...")
    from chat.services import get_rag_chain
    
    print("Getting RAG chain...")
    rag_chain = get_rag_chain()
    print(f"RAG chain obtained: {type(rag_chain)}")
    
    print("Testing with a sample query...")
    result = rag_chain.invoke({"input": "What is the Constitution of Pakistan?"})
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
    print("SUCCESS!")
    
except Exception as e:
    import traceback
    print(f"ERROR: {str(e)}")
    print("Traceback:")
    traceback.print_exc()

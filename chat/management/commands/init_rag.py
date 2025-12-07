"""
Management command to initialize the RAG chain at startup.
This prevents the first request from timing out while downloading embeddings.
"""
from django.core.management.base import BaseCommand
from chat.services import get_rag_chain
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize the RAG chain for the chatbot'

    def handle(self, *args, **options):
        try:
            self.stdout.write('Initializing RAG chain...')
            logger.info('Starting RAG chain initialization via management command')
            
            rag_chain = get_rag_chain()
            
            self.stdout.write(
                self.style.SUCCESS('RAG chain initialized successfully!')
            )
            logger.info('RAG chain initialized successfully')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error initializing RAG chain: {str(e)}')
            )
            logger.exception(f'Error initializing RAG chain: {str(e)}')
            raise

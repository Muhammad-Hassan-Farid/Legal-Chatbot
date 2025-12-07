from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('chat/', views.chat_page, name='chat_page'),
    path('get/', views.chat_api, name='chat_api'),
    path('transcribe/', views.transcribe_audio, name='transcribe_audio'),
    path('synthesize/', views.synthesize_speech, name='synthesize_speech'),
]


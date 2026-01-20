from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('chat/', views.chat_page, name='chat_page'),
    path('comparison/', views.comparison_page, name='comparison_page'),
    path('get/', views.chat_api, name='chat_api'),
    path('transcribe/', views.transcribe_audio, name='transcribe_audio'),
    path('synthesize/', views.synthesize_speech, name='synthesize_speech'),
    path('compare/', views.compare_with_qanoonmate, name='compare_with_qanoonmate'),
    path('compare-lexiber/', views.compare_with_lexiber, name='compare_with_lexiber'),
    path('compare-lexa/', views.compare_with_lexa, name='compare_with_lexa'),
    path('compare-all/', views.compare_all_platforms, name='compare_all_platforms'),
]


from django.urls import path

from apps.main.views import (
    CharecterVoiceListView, 
    NatureSoundsListView, 
    BackgroundImageView,
    MeditationGenerateView,
    MeditationDetailView,
    MeditationArchiveView
)

urlpatterns = [
    path('charecter-voice/', CharecterVoiceListView.as_view(), name='charecter-voice'),
    path('nature-sounds/', NatureSoundsListView.as_view(), name='nature-sounds'),
    path('background-image/', BackgroundImageView.as_view(), name='background-image'),
    path('meditation/generate/', MeditationGenerateView.as_view(), name='meditation-generate'),
    path('meditation/archive/', MeditationArchiveView.as_view(), name='meditation-archive'),
    path('meditation/<int:pk>/', MeditationDetailView.as_view(), name='meditation-detail'),
]
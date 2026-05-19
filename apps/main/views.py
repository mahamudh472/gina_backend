from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum

from apps.main.models import CharecterVoice, NatureSounds, BackgroundImage, Meditation, MeditationSteps
from apps.main.serializers import (
    CharecterVoiceSerializer, 
    NatureSoundsSerializer, 
    BackgroundImageSerializer,
    MeditationGenerateSerializer,
    MeditationGenerationResponseSerializer,
    MeditationSerializer,
    MeditationArchiveSerializer
)
from apps.main.services import create_generated_meditation

class CharecterVoiceListView(generics.ListAPIView):

    serializer_class = CharecterVoiceSerializer
    queryset = CharecterVoice.objects.all()

class NatureSoundsListView(generics.ListAPIView):
    serializer_class = NatureSoundsSerializer
    queryset = NatureSounds.objects.filter(is_active=True)

class BackgroundImageView(generics.ListAPIView):
    serializer_class = BackgroundImageSerializer
    queryset = BackgroundImage.objects.filter(is_active=True)

class MeditationGenerateView(APIView):
    """
    Endpoint to generate a new meditation with personalized steps.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = MeditationGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Delegate generation to the service layer
        meditation = create_generated_meditation(serializer.validated_data, user=request.user)
        
        # Serialize the fully generated meditation with steps and return
        response_serializer = MeditationGenerationResponseSerializer(
            meditation, 
            context={'request': request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class MeditationDetailView(generics.RetrieveAPIView):
    """
    Endpoint to retrieve a meditation by its ID, returning detailed related data.
    """
    serializer_class = MeditationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Allow users to retrieve their own meditations
        return Meditation.objects.filter(user=self.request.user)

class MeditationArchivePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class MeditationArchiveView(generics.ListAPIView):
    """
    Endpoint to retrieve the user's meditation archive.
    """
    serializer_class = MeditationArchiveSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MeditationArchivePagination

    def get_queryset(self):
        return Meditation.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        all_ids = list(queryset.values_list('id', flat=True))
        overall_duration = MeditationSteps.objects.filter(meditation__user=request.user).aggregate(Sum('duration'))['duration__sum']
        overall_duration_seconds = overall_duration.total_seconds() if overall_duration else 0
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            # Inject extra custom fields to paginated response
            response.data['all_meditation_ids'] = all_ids
            response.data['overall_total_duration'] = overall_duration_seconds
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'all_meditation_ids': all_ids,
            'overall_total_duration': overall_duration_seconds,
            'results': serializer.data
        })
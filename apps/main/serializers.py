from rest_framework import serializers
from apps.main.models import CharecterVoice, NatureSounds, BackgroundImage, Meditation, MeditationSteps, MeditationCategory, Music


class CharecterVoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharecterVoice
        fields = ['id','name','avatar_url','short_description','tags', 'file']

class NatureSoundsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NatureSounds
        fields = ['id','name', 'file']

class BackgroundImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundImage
        fields = ['id','name', 'file']

class MusicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Music
        fields = ['id', 'name', 'file']


class MeditationStepsSerializer(serializers.ModelSerializer):
    duration_percentage = serializers.SerializerMethodField()

    class Meta:
        model = MeditationSteps
        fields = ['id', 'step_type', 'content', 'audio_file', 'duration', 'duration_percentage', 'created_at']

    def get_duration_percentage(self, obj):
        meditation = getattr(obj, 'meditation', None)
        if not meditation:
            return 0.0
        total = meditation.total_duration
        if total and obj.duration:
            total_seconds = total.total_seconds()
            step_seconds = obj.duration.total_seconds()
            if total_seconds > 0:
                return round((step_seconds / total_seconds) * 100, 2)
        return 0.0

class MeditationSerializer(serializers.ModelSerializer):
    steps = serializers.SerializerMethodField()
    charecter_voice = CharecterVoiceSerializer(read_only=True)
    nature_sound = NatureSoundsSerializer(read_only=True)
    background_image = BackgroundImageSerializer(read_only=True)
    music = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()

    def get_banner_url(self, obj):
        request = self.context.get('request')
        if obj.banner_url and request:
            return request.build_absolute_uri(obj.banner_url)
        return obj.banner_url

    class Meta:
        model = Meditation
        fields = [
            'id', 'title', 'banner_url', 'background_image', 'charecter_voice',
            'nature_sound', 'music', 'experience_question_answer', 'category', 'created_at',
            'steps', 'total_duration'
        ]

    def get_steps(self, obj):
        return MeditationStepsSerializer(obj.get_combined_steps(), many=True, context=self.context).data

    def get_total_duration(self, obj):
        duration = obj.total_duration
        return duration.total_seconds() if duration else 0

    def get_music(self, obj):
        active_music = Music.objects.filter(category=obj.category, is_active=True).first()
        if active_music:
            return MusicSerializer(active_music, context=self.context).data
        return None

class MeditationArchiveSerializer(serializers.ModelSerializer):
    total_duration = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Meditation
        fields = ['id', 'banner_url', 'category', 'category_name', 'created_at', 'total_duration']

    def get_banner_url(self, obj):
        request = self.context.get('request')
        if obj.banner_url and request:
            return request.build_absolute_uri(obj.banner_url)
        return obj.banner_url

    def get_total_duration(self, obj):
        duration = obj.total_duration
        return duration.total_seconds() if duration else 0

class MeditationGenerationResponseSerializer(serializers.ModelSerializer):
    meditation_id = serializers.IntegerField(source='id')
    steps = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()

    class Meta:
        model = Meditation
        fields = ['id', 'meditation_id', 'total_duration', 'steps']

    def get_steps(self, obj):
        return MeditationStepsSerializer(obj.get_combined_steps(), many=True, context=self.context).data

    def get_total_duration(self, obj):
        duration = obj.total_duration
        return duration.total_seconds() if duration else 0


class MeditationGenerateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=MeditationCategory.choices)
    charecter_voice_id = serializers.IntegerField()
    experience_question_answers = serializers.JSONField()
    nature_sound_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    background_image_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_charecter_voice_id(self, value):
        if not CharecterVoice.objects.filter(id=value).exists():
            raise serializers.ValidationError("Character voice does not exist.")
        return value

    def validate_background_image_id(self, value):
        if value is not None and not BackgroundImage.objects.filter(id=value).exists():
            raise serializers.ValidationError("Background image does not exist.")
        return value
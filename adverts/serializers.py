# adverts/serializers.py
from rest_framework import serializers
from .models import AdvertThumbnail

class AdvertThumbnailSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = AdvertThumbnail
        fields = ['id', 'title', 'image_url', 'uploaded_at']

    def get_image_url(self, obj):
        """Return full image URL for frontend use."""
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return ""
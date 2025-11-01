from django.db import models

# Create your models here.
# adverts/models.py
from django.db import models

class AdvertThumbnail(models.Model):
    title = models.CharField(max_length=150, blank=True, null=True)
    image = models.ImageField(upload_to='thumbnails/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Advert {self.id}"

    @property
    def image_url(self):
        """Return full image URL for frontend use"""
        try:
            return self.image.url
        except:
            return ""

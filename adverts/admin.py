from django.contrib import admin

# Register your models here.
# adverts/admin.py
from django.contrib import admin
from .models import AdvertThumbnail

@admin.register(AdvertThumbnail)
class AdvertThumbnailAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'uploaded_at', 'image_preview']
    list_filter = ['uploaded_at']
    search_fields = ['title']
    readonly_fields = ['uploaded_at', 'image_preview']
    
    def image_preview(self, obj):
        """Show image preview in admin."""
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-width: 100px; max-height: 100px;" />'
        return "No image"
    image_preview.allow_tags = True
    image_preview.short_description = "Preview"
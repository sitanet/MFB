from django.db import models
import uuid

# Create your models here.

class PsbBank(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    bank_code = models.CharField(max_length=20, unique=True)
    bank_name = models.CharField(max_length=100)
    bank_long_code = models.CharField(max_length=50, blank=True, null=True)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "9PSB Bank"
        verbose_name_plural = "9PSB Banks"
        ordering = ['bank_name']

    def __str__(self):
        return f"{self.bank_name} ({self.bank_code})"

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


class WebhookNotification(models.Model):
    """
    Store all webhook notifications from 9PSB for tracking and reconciliation.
    Helps handle duplicates, failures, and delays.
    """
    STATUS_CHOICES = (
        ('received', 'Received'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('duplicate', 'Duplicate'),
        ('verified', 'Verified'),
    )
    
    EVENT_TYPES = (
        ('transfer', 'Transfer/Inflow'),
        ('account-upgrade', 'Account Upgrade'),
    )
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Webhook details
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    session_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    transaction_ref = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    order_ref = models.CharField(max_length=100, blank=True, null=True)
    
    # Account details
    account_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Sender details
    sender_account = models.CharField(max_length=20, blank=True, null=True)
    sender_name = models.CharField(max_length=200, blank=True, null=True)
    sender_bank = models.CharField(max_length=100, blank=True, null=True)
    narration = models.TextField(blank=True, null=True)
    
    # Raw payload for debugging
    raw_payload = models.JSONField(null=True, blank=True)
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Verification
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_response = models.JSONField(null=True, blank=True)
    
    # Retry tracking
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Webhook Notification"
        verbose_name_plural = "Webhook Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id', 'account_number']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.transaction_ref or self.session_id} - {self.status}"

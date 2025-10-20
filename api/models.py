from django.db import models

# Create your models here.
from django.db import models
from customers.models import Customer
from django.utils.timezone import now

class Notification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ('transaction_alert', 'Transaction Alert'),
        ('low_balance', 'Low Balance'),
        ('approval', 'Approval'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]

    notification_id = models.CharField(max_length=20, unique=True)
    type = models.CharField(max_length=30, choices=NOTIF_TYPE_CHOICES)
    recipient = models.ForeignKey(Customer, on_delete=models.CASCADE)
    channel = models.CharField(max_length=10)  # SMS, PUSH, EMAIL
    transaction_id = models.CharField(max_length=50, null=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"{self.notification_id} - {self.type} - {self.status}"




from django.db import models
from django.conf import settings

class Beneficiary(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,   # ✅ Use this instead of User
        on_delete=models.CASCADE,
        related_name='beneficiaries',
        help_text="The user who owns this beneficiary."
    )
    name = models.CharField(max_length=100, help_text="Full name of the beneficiary.")
    bank_name = models.CharField(max_length=100, help_text="Bank name of the beneficiary.")
    account_number = models.CharField(max_length=20, help_text="Bank account number.")
    phone_number = models.CharField(max_length=15, blank=True, null=True, help_text="Optional phone number.")
    nickname = models.CharField(max_length=50, blank=True, null=True, help_text="Nickname for quick reference.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Beneficiary'
        verbose_name_plural = 'Beneficiaries'
        unique_together = ('user', 'account_number')  # ✅ prevents duplicate beneficiary for same user

    def __str__(self):
        return f"{self.name} ({self.account_number})"


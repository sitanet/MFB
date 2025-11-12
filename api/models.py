from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

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
        settings.AUTH_USER_MODEL,   
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
        unique_together = ('user', 'account_number')  

    def __str__(self):
        return f"{self.name} ({self.account_number})"

# OTP Storage Models for Signup Flow
# Add these to your Django app's models.py or create a new app

from django.db import models
from django.utils import timezone
from datetime import timedelta
import string
import random

class OTPVerification(models.Model):
    """Model to store OTP verification data - replaces sessions"""
    
    account_number = models.CharField(max_length=20, db_index=True)
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=6)
    attempts = models.IntegerField(default=0)
    customer_id = models.IntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'otp_verification'
        indexes = [
            models.Index(fields=['account_number', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.account_number} - {self.otp_code}"
    
    @classmethod
    def create_otp(cls, account_number, phone_number, customer_id=None):
        """Create a new OTP for account verification"""
        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Clear any existing OTPs for this account
        cls.objects.filter(account_number=account_number).delete()
        
        # Create new OTP with 5-minute expiry
        otp = cls.objects.create(
            account_number=account_number,
            phone_number=phone_number,
            otp_code=otp_code,
            customer_id=customer_id,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        return otp
    
    @classmethod
    def verify_otp(cls, account_number, otp_code):
        """Verify OTP code and return result"""
        try:
            otp = cls.objects.get(
                account_number=account_number,
                is_verified=False,
                is_expired=False
            )
            
            # Check if expired
            if timezone.now() > otp.expires_at:
                otp.is_expired = True
                otp.save()
                return {'success': False, 'error': 'OTP has expired', 'otp': None}
            
            # Check attempt limit
            if otp.attempts >= 3:
                otp.is_expired = True
                otp.save()
                return {'success': False, 'error': 'Too many failed attempts', 'otp': None}
            
            # Verify code
            if otp.otp_code != otp_code:
                otp.attempts += 1
                otp.save()
                remaining = 3 - otp.attempts
                return {
                    'success': False, 
                    'error': f'Invalid OTP. {remaining} attempts remaining',
                    'otp': None
                }
            
            # Success
            otp.is_verified = True
            otp.used_at = timezone.now()
            otp.save()
            
            return {'success': True, 'error': None, 'otp': otp}
            
        except cls.DoesNotExist:
            return {'success': False, 'error': 'OTP not found or expired', 'otp': None}
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return (
            not self.is_verified and 
            not self.is_expired and 
            timezone.now() <= self.expires_at and
            self.attempts < 3
        )


class RegistrationToken(models.Model):
    """Model to store registration tokens after OTP verification"""
    
    account_number = models.CharField(max_length=20, db_index=True)
    token = models.CharField(max_length=64, unique=True)
    customer_id = models.IntegerField()
    verified_phone = models.CharField(max_length=20)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'registration_token'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Token for {self.account_number}"
    
    @classmethod
    def create_token(cls, account_number, customer_id, verified_phone):
        """Create a new registration token"""
        # Generate unique token
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        
        # Clear any existing tokens for this account
        cls.objects.filter(account_number=account_number).delete()
        
        # Create new token with 10-minute expiry
        reg_token = cls.objects.create(
            account_number=account_number,
            token=token,
            customer_id=customer_id,
            verified_phone=verified_phone,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        return reg_token
    
    @classmethod
    def verify_token(cls, account_number, token):
        """Verify registration token"""
        try:
            reg_token = cls.objects.get(
                account_number=account_number,
                token=token,
                is_used=False
            )
            
            # Check if expired
            if timezone.now() > reg_token.expires_at:
                return {'success': False, 'error': 'Token expired', 'token_obj': None}
            
            return {'success': True, 'error': None, 'token_obj': reg_token}
            
        except cls.DoesNotExist:
            return {'success': False, 'error': 'Invalid token', 'token_obj': None}
    
    def mark_used(self):
        """Mark token as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
    
    def is_valid(self):
        """Check if token is still valid"""
        return (
            not self.is_used and 
            timezone.now() <= self.expires_at
        )
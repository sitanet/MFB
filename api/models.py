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












# api/models.py (Add these models to your existing models.py file)

from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class GlobalTransferFeeConfiguration(models.Model):
    """
    GLOBAL fee configuration that applies to ALL customers
    Only ONE active configuration should exist at a time
    """
    
    TRANSFER_TYPE_CHOICES = [
        ('other_bank', 'Transfer to Other Bank'),
        ('international', 'International Transfer'),
    ]
    
    # Basic Configuration
    name = models.CharField(max_length=100, default='Other Bank Transfer Fee')
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES, default='other_bank')
    base_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('10.00'),
        help_text="Base fee charged to ALL customers for other bank transfers"
    )
    
    # Global Free Transfer Allowances (applies to ALL customers)
    free_transfers_per_day = models.IntegerField(
        default=3, 
        help_text="Number of free transfers allowed per customer per day"
    )
    free_transfers_per_month = models.IntegerField(
        default=10, 
        help_text="Number of free transfers allowed per customer per month"
    )
    
    # Fee Collection Account (WHERE FEES FROM ALL CUSTOMERS GO)
    fee_gl_no = models.CharField(
        max_length=10, 
        help_text="GL number where ALL customer fees are credited"
    )
    fee_ac_no = models.CharField(
        max_length=20, 
        help_text="Account number where ALL customer fees are credited"
    )
    
    # Global Fee Rules
    min_amount_for_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('100.00'),
        help_text="Minimum transfer amount to charge fee (applies to ALL customers)"
    )
    max_daily_free_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('50000.00'),
        help_text="Maximum daily amount for free transfers per customer"
    )
    
    # System Status
    is_active = models.BooleanField(
        default=True,
        help_text="Only ONE configuration can be active at a time"
    )
    effective_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When this configuration becomes effective"
    )
    created_by = models.CharField(max_length=100, default='Admin')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'global_transfer_fee_configuration'
        verbose_name = 'Global Transfer Fee Configuration'
        verbose_name_plural = 'Global Transfer Fee Configurations'
        ordering = ['-created_at']
    
    def clean(self):
        """Ensure only one active configuration exists"""
        if self.is_active:
            # Check if another active config exists
            existing_active = GlobalTransferFeeConfiguration.objects.filter(
                is_active=True,
                transfer_type=self.transfer_type
            ).exclude(pk=self.pk)
            
            if existing_active.exists():
                raise ValidationError(
                    f"Another active {self.get_transfer_type_display()} "
                    f"configuration already exists. Only one can be active at a time."
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"{self.name} - ₦{self.base_fee} [{status}]"

class CustomerTransferUsage(models.Model):
    """
    Track individual customer usage for free transfer allowances
    NOTE: Fee amounts are GLOBAL - this only tracks usage counts
    """
    
    customer_id = models.CharField(max_length=50, db_index=True)
    date = models.DateField(db_index=True)
    month = models.CharField(max_length=7, db_index=True)  # Format: YYYY-MM
    
    # Daily usage counters (for free allowance tracking only)
    daily_transfer_count = models.IntegerField(default=0)
    daily_transfer_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    daily_fees_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Monthly usage counters (for free allowance tracking only)
    monthly_transfer_count = models.IntegerField(default=0)
    monthly_transfer_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    monthly_fees_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_transfer_usage'
        unique_together = ['customer_id', 'date']
        indexes = [
            models.Index(fields=['customer_id', 'date']),
            models.Index(fields=['customer_id', 'month']),
        ]
    
    def __str__(self):
        return f"Customer {self.customer_id} - {self.date} ({self.daily_transfer_count} transfers)"

class GlobalTransferFeeTransaction(models.Model):
    """
    Audit log for ALL fee transactions across ALL customers
    Records every fee charged or waived
    """
    
    # Customer Information
    customer_id = models.CharField(max_length=50, db_index=True)
    customer_account = models.CharField(max_length=20)
    transfer_reference = models.CharField(max_length=100, db_index=True)
    
    # Fee Configuration Used (snapshot)
    fee_config_name = models.CharField(max_length=100)
    base_fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Waiver Information
    was_waived = models.BooleanField(default=False)
    waiver_reason = models.CharField(max_length=200, blank=True)
    free_transfers_remaining_daily = models.IntegerField(default=0)
    free_transfers_remaining_monthly = models.IntegerField(default=0)
    
    # Transfer Details
    transfer_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_debited = models.DecimalField(max_digits=15, decimal_places=2)
    destination_bank = models.CharField(max_length=10)
    destination_account = models.CharField(max_length=20)
    destination_name = models.CharField(max_length=100, blank=True)
    
    # Accounting Entries (where money moved)
    fee_gl_no = models.CharField(max_length=10)
    fee_ac_no = models.CharField(max_length=20)
    customer_gl_no = models.CharField(max_length=10)
    customer_ac_no = models.CharField(max_length=20)
    fee_transaction_ref = models.CharField(max_length=100, blank=True)
    
    # System Information
    processed_at = models.DateTimeField(auto_now_add=True)
    processing_date = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = 'global_transfer_fee_transactions'
        verbose_name = 'Transfer Fee Transaction (All Customers)'
        verbose_name_plural = 'Transfer Fee Transactions (All Customers)'
        indexes = [
            models.Index(fields=['customer_id', 'processed_at']),
            models.Index(fields=['transfer_reference']),
            models.Index(fields=['processing_date']),
            models.Index(fields=['was_waived']),
        ]
    
    def __str__(self):
        status = "WAIVED" if self.was_waived else f"₦{self.applied_fee_amount}"
        return f"{self.customer_id} - {self.transfer_reference} - {status}"
from django.utils import timezone
from django.db import models
from django.conf import settings  # Add this import
from django.contrib.auth.models import User  # Import the User model
from django.db import models
from django.utils.timezone import now  # Import the 'now' function

class Company(models.Model):
    company_name = models.CharField(max_length=100, null=True, blank=True)
 
    contact_person = models.CharField(max_length=100)
    office_address = models.CharField(max_length=100)
    contact_phone_no = models.CharField(max_length=100)
    session_date = models.DateField(null=True, blank=True)
    system_date_date = models.DateField(null=True, blank=True)
    registration_date = models.DateField()
    expiration_date = models.DateField()
    license_key = models.CharField(max_length=50)
    session_status = models.CharField(max_length=10, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    float_account_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="The 9PSB wallet or float account number assigned to this company."
    )
    last_notification_date = models.DateField(null=True, blank=True)

    float_gl_no = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="GL number linked to the company’s float account."
    )
    float_ac_no = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Internal ledger account number linked to the float account."
    )

    mobile_teller_gl_no = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="GL number linked to the company’s Mobile Teller account."
    )
    mobile_teller_ac_no = models.CharField(
            max_length=20,
            null=True,
            blank=True,
            help_text="Internal ledger account number linked to the Mobile Teller account."
        )




    def __str__(self):
            return str(self.company_name)
    


from django.utils.timezone import now, timedelta

class Branch(models.Model):
    PLAN_CHOICES = [
        ("Starter", "Starter"),
        ("Basic", "Basic"),
        ("Premium", "Premium"),
        ("Professional", "Professional"),
        ("Ultimate", "Ultimate"),
        ("Enterprise", "Enterprise"),
    ]

    # models.py
    # user = models.ForeignKey(
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.CASCADE,
    #     null=True,
    #     blank=True,
    #     related_name="branches"   # ✅ avoids clash with User.branch
    # )


    company_name = models.CharField(max_length=100)
    # company = models.CharField(max_length=100, blank=True, null=True)
    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="branches"
    )
    branch_code = models.CharField(max_length=6)
    branch_name = models.CharField(max_length=90)
    logo = models.ImageField(upload_to='branch_logos/', blank=True, null=True)
    address = models.TextField()
    cac_number = models.CharField(max_length=100)
    license_number = models.CharField(max_length=100)
    company_type = models.CharField(max_length=50)
    bvn_number = models.CharField(max_length=11)
    phone_number = models.CharField(max_length=20)
    phone_verified = models.BooleanField(default=False)

    head_office = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    plan = models.CharField(max_length=15, choices=PLAN_CHOICES, default="Starter")
    session_date = models.DateField(null=True, blank=True, default=now)
    system_date_date = models.DateField(null=True, blank=True)
    session_status = models.CharField(max_length=10, null=True, blank=True)

    # ✅ New expire date field
    expire_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def save(self, *args, **kwargs):
        # ❌ REMOVE THIS LINE:
        # self.company = self.branch_name   ← DELETE IT

        # Only set expire_date if not already set (e.g., on creation)
        if not self.expire_date and not self.pk:  # only on first save
            self.expire_date = timezone.now().date() + timedelta(days=30)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company_name} - {self.branch_name} - {self.plan}"


class SmsDelivery(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('error', 'Error')
    ]
    
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True)
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"SMS to {self.phone_number} ({self.status})"
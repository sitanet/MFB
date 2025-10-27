import random
from django.db import models
from django.core.exceptions import ValidationError
from accounts_admin.models import Account, Account_Officer, Category, Id_card_type, Region
from company.models import Company, Branch
from django.db.models import UniqueConstraint






class Group(models.Model):
    group_name = models.CharField(max_length=100, unique=True)
    group_code = models.CharField(max_length=50, unique=True)
    created_date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.group_name

        
class Customer(models.Model):
    photo = models.ImageField(upload_to='photo/customer', default='images/avatar.jpg')  # Customer Photo
    sign = models.ImageField(upload_to='sign/customer', default='images/avatar.jpg') 
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="customer", 
                               null=True, blank=True)
    gl_no = models.CharField(max_length=20, null=True, blank=True)
    ac_no = models.CharField(max_length=20, null=True, blank=True)  # Customer Number

    first_name = models.CharField(max_length=100, null=True, blank=True)  # Customer Name
    middle_name = models.CharField(max_length=100, null=True, blank=True)   
    last_name = models.CharField(max_length=100, null=True, blank=True)   
    dob = models.DateField(null=True, blank=True)   
    email = models.EmailField(max_length=100, null=True, blank=True)  # Date of Birth
    cust_sex = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female'), ('O', 'Other')), 
                                null=True, blank=True)  # Gender
    marital_status = models.CharField(max_length=1, choices=(('S', 'Single'), ('M', 'Married'), ('W', 'Widow')), 
                                      null=True, blank=True)  
    address = models.TextField(max_length=100, null=True, blank=True)  # Customer Address
    nationality = models.CharField(max_length=30, null=True, blank=True) 
    state = models.CharField(max_length=30, null=True, blank=True) 
    phone_no = models.CharField(max_length=20, null=True, blank=True)  # Phone Number
    mobile = models.CharField(max_length=20, null=True, blank=True)  # Mobile Number
    id_card = models.CharField(max_length=20, null=True, blank=True) 
    id_type = models.ForeignKey(Id_card_type, on_delete=models.CASCADE, null=True, blank=True)  # ID Card Number
    ref_no = models.CharField(max_length=20, null=True, blank=True) 
    occupation = models.CharField(max_length=20, null=True, blank=True)  # Occupation
    cust_cat = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)  # Customer Category
    internal = models.BooleanField(default=False, null=True, blank=True)  # Internal Customer (True/False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)     
    credit_officer = models.ForeignKey(Account_Officer, on_delete=models.CASCADE, null=True, blank=True)  # Credit Officer Name
    
    group_code = models.CharField(max_length=20, null=True, blank=True)  # Group Code
    group_name = models.CharField(max_length=50, null=True, blank=True)  # Group Name
    reg_date = models.DateField(null=True, blank=True)  # Registration Date
    close_date = models.DateField(null=True, blank=True)  # Closing Date (if applicable)
    status = models.CharField(max_length=1, choices=(('A', 'Active'), ('D', 'Dormant'), ('P', 'Pending')), 
                              null=True, blank=True)  # Status
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.00)
    label = models.CharField(max_length=1, null=True, blank=True)  
    loan = models.CharField(max_length=1, default='F', null=True, blank=True)
    sms = models.BooleanField(default=False)
    email_alert = models.BooleanField(default=True)

        # 🔑 New fields
    bvn = models.CharField(max_length=11, blank=True, null=True)
    nin = models.CharField(max_length=16, blank=True, null=True)

    # 🔑 NEW FIELD for 9PSB Wallet
    wallet_account = models.CharField(max_length=20, blank=True, null=True, unique=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_code = models.CharField(max_length=20, blank=True, null=True)

    transfer_limit = models.DecimalField(
    max_digits=12, 
    decimal_places=2, 
    blank=True, 
    null=True, 
    default=0.00,
    help_text="Maximum transfer limit in Naira."
)



# Group
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')



# Corporate
    registration_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    contact_person_name = models.CharField(max_length=255, blank=True, null=True)
    contact_person_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_person_email = models.EmailField(blank=True, null=True)
    office_address = models.TextField(blank=True, null=True)
    office_phone = models.CharField(max_length=20, blank=True, null=True)
    office_email = models.EmailField(blank=True, null=True)
    date_registered = models.DateField(auto_now_add=True, blank=True, null=True)
    is_company = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['first_name', 'middle_name', 'last_name', 'gl_no', 'branch'], 
                             name='unique_name_combination'),
            UniqueConstraint(fields=['gl_no', 'ac_no', 'branch'], 
                             name='unique_gl_ac_branch_combination')
        ]

    def gl_no_gl_no(self):
        return self.gl_no.gl_no

    def __str__(self):
        return self.get_full_name()

    # def get_full_name(self):
    #     if self.middle_name:
    #         return f"{self.first_name} {self.middle_name} {self.last_name}"
    #     return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        if self.is_company:
            return self.registration_number or "Unnamed Company"
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"


    def save(self, *args, **kwargs):
        if self.branch:
            # Define plan limits
            plan_limits = {
                "Starter": 300,
                "Basic": 500,
                "Premium": 700,
                "Professional": 1000,
                "Ultimate": None,  # Unlimited
                "Enterprise": None,  # Unlimited
            }

            # Get the branch plan
            branch_plan = self.branch.plan  # Assuming `plan` is a field in Branch model
            customer_count = Customer.objects.filter(branch=self.branch).count()

            # Check if the plan has a limit and enforce it
            if plan_limits.get(branch_plan) is not None and customer_count >= plan_limits[branch_plan]:
                raise ValueError(
                    f"Cannot add more customers. The '{branch_plan}' plan allows only {plan_limits[branch_plan]} customers."
                )

        super().save(*args, **kwargs)


# customers/models.py
import uuid
import random
import secrets
from django.db import models

def _luhn_check_digit(number_without_check: str) -> int:
    total = 0
    reverse = list(map(int, number_without_check[::-1]))
    for i, d in enumerate(reverse, start=1):
        if i % 2 == 1:
            total += d
        else:
            d2 = d * 2
            if d2 > 9:
                d2 -= 9
            total += d2
    return (10 - (total % 10)) % 10

def generate_card_number(prefix: str = "539999", length: int = 16) -> str:
    if not prefix.isdigit():
        raise ValueError("prefix must be digits")
    if len(prefix) >= length:
        raise ValueError("prefix too long")
    body_len = length - len(prefix) - 1
    body = ''.join(str(random.randint(0, 9)) for _ in range(body_len))
    check = _luhn_check_digit(prefix + body)
    return prefix + body + str(check)

def generate_cvv(length: int = 3) -> str:
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))


class VirtualCard(models.Model):
    STATUS_CHOICES = (
        ('pending', 'pending'),
        ('active', 'active'),
        ('inactive', 'inactive'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='virtual_cards')
    gl_no = models.CharField(max_length=5)           # fixed: "20501"
    ac_no = models.CharField(max_length=5)           # unique per GL
    card_number = models.CharField(max_length=19, unique=True, null=True, blank=True)
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    cvv = models.CharField(max_length=4)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['gl_no', 'ac_no'], name='uniq_virtual_card_gl_ac'),
        ]

    def save(self, *args, **kwargs):
        if not self.card_number:
            for _ in range(100):
                candidate = generate_card_number()
                if not type(self).objects.filter(card_number=candidate).exists():
                    self.card_number = candidate
                    break
        if not self.cvv:
            self.cvv = generate_cvv(3)
        super().save(*args, **kwargs)





from accounts.models import User


class KYCDocument(models.Model):
    DOCUMENT_TYPES = (
        ('PASSPORT', 'Passport'),
        ('NATIONAL_ID', 'National ID'),
        ('PROOF_OF_ADDRESS', 'Proof of Address'),
        # Add more as needed
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='kyc_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.get_document_type_display()}"





class FixedDepositAccount(models.Model):
    """
    Represents a fixed deposit account linked to a customer.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    fixed_gl_no = models.CharField(max_length=20, unique=True)
    fixed_ac_no = models.CharField(max_length=20, unique=True)  # Unique FD Account Number
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return f"FD-{self.fixed_ac_no} | {self.customer}"
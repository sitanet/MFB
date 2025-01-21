from django.utils import timezone
from django.db import models

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



    def __str__(self):
            return str(self.company_name)
    

from django.db import models
from django.utils.timezone import now  # Import the 'now' function

class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    branch_code = models.CharField(max_length=6)
    branch_name = models.CharField(max_length=90)
    session_date = models.DateField(null=True, blank=True, default=now)  # Now imported and used here
    system_date_date = models.DateField(null=True, blank=True)
    session_status = models.CharField(max_length=10, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.branch_name} ({self.branch_code})"

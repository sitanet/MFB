import random
from django.db import models
from accounts_admin.models import Account, Account_Officer, Category, Id_card_type, Region
from company.models import Company, Branch
from django.db.models import UniqueConstraint

class Customer(models.Model):
    photo = models.ImageField(upload_to='photo/customer', default='images/avatar.jpg' )  # Customer Photo
    sign = models.ImageField(upload_to='sign/customer', default='images/avatar.jpg' ) 
    # photos = models.ImageField(upload_to='images/')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="customer", 
    null=True, blank=True)
    gl_no = models.CharField(max_length=20, null=True, blank=True)
    ac_no = models.CharField(max_length=20, null=True, blank=True)  # Customer Number
    
    
    first_name = models.CharField(max_length=100, null=True, blank=True)               # Customer Name
    middle_name = models.CharField(max_length=100, null=True, blank=True)   
    last_name = models.CharField(max_length=100, null=True, blank=True)   
    dob = models.DateField(null=True, blank=True)   
    email = models.EmailField(max_length=100,  null=True, blank=True)                           # Date of Birth
    cust_sex = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female'), ('O', 'Other')), null=True, blank=True)  # Gender
    marital_status = models.CharField(max_length=1, choices=(('S', 'Single'), ('M', 'Married'), ('W', 'WIDOW')), null=True, blank=True)  # Gender
    address = models.TextField(max_length=100, null=True, blank=True)                          # Customer Address
    nationality = models.CharField(max_length=30, null=True, blank=True) 
    state = models.CharField(max_length=30, null=True, blank=True) 
    phone_no = models.CharField(max_length=20, null=True, blank=True)            # Phone Number
    mobile = models.CharField(max_length=20, null=True, blank=True)              # Mobile Number
    id_card = models.CharField(max_length=20, null=True, blank=True) 
    id_type = models.ForeignKey(Id_card_type, on_delete=models.CASCADE, null=True, blank=True)             # ID Card Number
    ref_no = models.CharField(max_length=20, null=True, blank=True) 
    occupation = models.CharField(max_length=20, null=True, blank=True)             # Reference Number
    cust_cat = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)             # Customer Category
    internal = models.BooleanField(default=False, null=True, blank=True)         # Internal Customer (True/False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)     
    credit_officer = models.ForeignKey(Account_Officer, on_delete=models.CASCADE, null=True, blank=True)     # Credit Officer Name
    
    group_code = models.CharField(max_length=20, null=True, blank=True)          # Group Code
    group_name = models.CharField(max_length=50, null=True, blank=True)          # Group Name
    reg_date = models.DateField(null=True, blank=True)                          # Registration Date
    close_date = models.DateField(null=True, blank=True)   # Closing Date (if applicable)
    status = models.CharField(max_length=1, choices=(('A', 'Active'), ('D', 'Dormant'), ('P', 'Pending')), null=True, blank=True)  # Status
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.00)
    label = models.CharField(max_length=1, null=True, blank=True)  
    loan = models.CharField(max_length=1, default='F', null=True, blank=True)
    sms = models.BooleanField(default=False)
    


    class Meta:
        constraints = [
            UniqueConstraint(fields=['first_name', 'middle_name', 'last_name', 'gl_no', 'branch'], name='unique_name_combination'),
            UniqueConstraint(fields=['gl_no', 'ac_no', 'branch'], name='unique_gl_ac_branch_combination')
        ]
    
    # def save(self, *args, **kwargs):
    #     if not self.cust_no:
    #         # Generate a unique 6-digit cust_no
    #         while True:
    #             unique_no = random.randint(100000, 999999)
    #             if not Customer.objects.filter(cust_no=unique_no).exists():
    #                 self.cust_no = unique_no
    #                 break
    #     super().save(*args, **kwargs)

    # def __str__(self):
    #     return self.first_name
    
    def gl_no_gl_no(self):
        return self.gl_no.gl_no
    
    # def get_full_name(self):
    #     if self.middle_name:
    #         return f"{self.first_name} {self.middle_name} {self.last_name}"
    #     else:
    #         return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        else:
            return f"{self.first_name} {self.last_name}"


# If you're using Django's built-in User model, you can create a one-to-one relationship with the User model.
# from django.contrib.auth.models import User

# class CustomerProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

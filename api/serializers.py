# api/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from accounts.models import User
from django.contrib.auth import authenticate, get_user_model
User = get_user_model()

from django.contrib.auth import authenticate, get_user_model
User = get_user_model()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username_or_email = data['username']
        password = data['password']

        # First try normal username login
        user = authenticate(username=username_or_email, password=password)

        # If that fails, try email lookup
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        return user

class ActivationSerializer(serializers.Serializer):
    username = serializers.CharField()  # you can rename to 'email' if you like
    activation_code = serializers.CharField()

    def validate(self, data):
        try:
            user = User.objects.get(
                email=data['username'],  # use email instead of username
                activation_code=data['activation_code']
            )
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid activation code")
        return user



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()






# customers/serializers.py

from rest_framework import serializers
from customers.models import Customer, KYCDocument
from accounts.models import User

class CustomerProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    account_number = serializers.CharField(source='ac_no', read_only=True)
    photo = serializers.ImageField(read_only=True)  # Photo is read-only in profile view
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)
    kyc_status = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'full_name', 'account_number', 'photo', 'branch_name',
            'kyc_status', 'email', 'phone_no', 'address'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_kyc_status(self, obj):
        # Simple logic: if at least one doc of each type exists → "Verified"
        required_types = {'PASSPORT', 'NATIONAL_ID', 'PROOF_OF_ADDRESS'}
        uploaded_types = set(obj.kyc_documents.values_list('document_type', flat=True))
        if required_types.issubset(uploaded_types):
            return "Verified"
        elif obj.kyc_documents.exists():
            return "Pending"
        else:
            return "Not Submitted"


class CustomerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['phone_no', 'email', 'address']
        # Only allow these fields to be updated

    def validate_email(self, value):
        # Ensure email is unique among customers (optional)
        user = self.context['request'].user
        if Customer.objects.filter(email=value).exclude(id=user.customer.id).exists():
            raise serializers.ValidationError("A customer with this email already exists.")
        return value


class KYCDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = ['document_type', 'file']
        read_only_fields = ['verified', 'verified_by', 'uploaded_at']

    def validate(self, data):
        customer = self.context['request'].user.customer
        doc_type = data['document_type']

        # Optional: Prevent duplicate uploads of same doc type
        if KYCDocument.objects.filter(customer=customer, document_type=doc_type).exists():
            raise serializers.ValidationError(f"You have already uploaded a {doc_type} document.")
        return data







# serializers.py
from rest_framework import serializers

class CustomerAccountSerializer(serializers.Serializer):
    gl_no = serializers.CharField(max_length=10, read_only=True)
    account_name = serializers.CharField(read_only=True, help_text="Product type code (e.g., SAVINGS, LOAN)")
    category = serializers.CharField(read_only=True, help_text="Accounting category: Assets, Liabilities, etc.")
    balance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    available_funds = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True, help_text="Customer account status")



from transactions.models import Memtrans
from accounts_admin.models import Account
from django.db.models import Sum




class GLAccountSerializer(serializers.Serializer):
    gl_no = serializers.CharField()
    product_type = serializers.CharField()
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)

class AccountDetailsSerializer(serializers.Serializer):
    account_number = serializers.CharField(source='ac_no')
    branch = serializers.CharField(source='branch.branch_name')  # or .name
    officer = serializers.SerializerMethodField()
    accounts = serializers.SerializerMethodField()

    def get_officer(self, obj):
        return obj.credit_officer.user if obj.credit_officer else "Not Assigned"

    def get_accounts(self, obj):
        gl_no_filter = self.context.get('gl_no')
        ac_no = obj.ac_no
        branch = obj.branch

        if gl_no_filter:
            # Single GL mode
            balance = Memtrans.objects.filter(
                ac_no=ac_no,
                gl_no=gl_no_filter,
                branch=branch,
                error='A'
            ).aggregate(total=Sum('amount'))['total'] or 0

            try:
                acc = Account.objects.get(gl_no=gl_no_filter)
                product_type = acc.product_type.internal_type if acc.product_type else "UNKNOWN"
            except Account.DoesNotExist:
                product_type = "INVALID_GL"

            return [{
                "gl_no": gl_no_filter,
                "product_type": product_type,
                "balance": balance
            }]

        else:
            # All GLs mode
            gl_nos = Memtrans.objects.filter(
                ac_no=ac_no,
                branch=branch,
                error='A'
            ).values_list('gl_no', flat=True).distinct()

            accounts = []
            for gl_no in gl_nos:
                # Get balance
                balance = Memtrans.objects.filter(
                    ac_no=ac_no,
                    gl_no=gl_no,
                    branch=branch,
                    error='A'
                ).aggregate(total=Sum('amount'))['total'] or 0

                # Get product type
                try:
                    acc = Account.objects.get(gl_no=gl_no)
                    product_type = acc.product_type.internal_type if acc.product_type else "UNKNOWN"
                except Account.DoesNotExist:
                    product_type = "INVALID_GL"

                accounts.append({
                    "gl_no": gl_no,
                    "product_type": product_type,
                    "balance": balance
                })
            return accounts




# api/serializers.py
from rest_framework import serializers

class TransactionSerializer(serializers.Serializer):
    trx_no = serializers.CharField()
    ses_date = serializers.DateField()
    description = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    gl_no = serializers.CharField()
    # Add more fields if needed: app_date, trx_type, etc.





from rest_framework import serializers

class BalanceEnquirySerializer(serializers.Serializer):
    account_number = serializers.CharField()
    gl_no = serializers.CharField(allow_null=True)  # Will be null for total balance
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    available_funds = serializers.DecimalField(max_digits=15, decimal_places=2)
    status = serializers.CharField()





# api/serializers.py
from rest_framework import serializers

class DepositPostingSerializer(serializers.Serializer):
    ac_no = serializers.CharField(max_length=20)
    branch_id = serializers.IntegerField()
    gl_no = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    description = serializers.CharField(max_length=100, required=False, default="Deposit")
    method = serializers.CharField(max_length=20, required=False, default="other")
    reference = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

class DepositHistorySerializer(serializers.Serializer):
    trx_no = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    gl_no = serializers.CharField()
    description = serializers.CharField()
    posted_by = serializers.CharField()
    method = serializers.CharField()
    date = serializers.DateField()
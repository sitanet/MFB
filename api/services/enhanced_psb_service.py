# api/services/enhanced_psb_service.py
"""
Enhanced 9PSB Service - Combines comprehensive functionality with parameter flexibility
"""

import requests
import hashlib
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from customers.models import Customer
import uuid

logger = logging.getLogger(__name__)

class Enhanced9PSBService:
    """
    Comprehensive 9PSB service with:
    - Flexible parameter handling (fixes original parameter mismatch)
    - Authentication with caching
    - Virtual account creation
    - Bank list management
    - Account validation
    - Fund transfers
    - Enhanced error handling
    """
    
    def __init__(self):
        self.public_key = getattr(settings, 'PSB_PUBLIC_KEY', '')
        self.private_key = getattr(settings, 'PSB_PRIVATE_KEY', '')
        # FIXED: Use the correct base URL that actually works
        self.base_url = getattr(settings, 'PSB_BASE_URL', 'https://baastest.9psb.com.ng/iva-api/v1')
        self.currency = getattr(settings, 'PSB_CURRENCY', 'NGN')
        self.country = getattr(settings, 'PSB_COUNTRY', 'NGA')
        self._token = None
        self._token_expires_at = None
    
    # ==========================================================
    # 🔐 AUTHENTICATION & TOKEN MANAGEMENT
    # ==========================================================
    
    def _is_token_valid(self):
        """Check if current token is valid with 5-minute buffer"""
        if not self._token or not self._token_expires_at:
            return False
        buffer_time = datetime.now() + timedelta(minutes=5)
        return self._token_expires_at > buffer_time
    
    def _get_cached_token(self):
        """Get token from Django cache"""
        cache_key = "psb_access_token"
        cached_data = cache.get(cache_key)
        if cached_data:
            self._token = cached_data['token']
            self._token_expires_at = cached_data['expires_at']
            return self._token if self._is_token_valid() else None
        return None
    
    def _cache_token(self, token, expires_in=3600):
        """Cache token with expiry"""
        expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
        cache_data = {
            'token': token,
            'expires_at': expires_at
        }
        cache.set("psb_access_token", cache_data, timeout=expires_in - 300)
        self._token = token
        self._token_expires_at = expires_at
    
    def authenticate(self):
        """
        Authenticate with 9PSB API using multiple endpoint strategies
        Returns access token or raises exception
        """
        # Check if we have a valid cached token
        cached_token = self._get_cached_token()
        if cached_token:
            logger.info("[9PSB] Using cached authentication token")
            return cached_token
        
        if not self.public_key or not self.private_key:
            raise Exception("9PSB API keys not configured in settings")
        
        logger.info(f"[9PSB] Authenticating with base URL: {self.base_url}")
        
        payload = {
            "publickey": self.public_key,
            "privatekey": self.private_key
        }
        
        # FIXED: Use correct authentication endpoints for iva-api/v1 base URL
        auth_endpoints = [
            "/merchant/virtualaccount/authenticate",  # Primary endpoint for iva-api/v1
            "/merchant/authenticate",  # Alternative
            "/authenticate"  # Fallback
        ]
        
        headers = {"Content-Type": "application/json"}
        last_error = None
        
        for endpoint in auth_endpoints:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"[9PSB] Trying authentication endpoint: {endpoint}")
            
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                # Handle non-JSON responses (HTML error pages)
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' in content_type:
                    logger.warning(f"[9PSB] HTML response from {endpoint} (likely 404)")
                    last_error = f"HTML response from {endpoint}"
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Check for successful authentication
                if data.get("code") == "00":
                    token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    
                    if token:
                        logger.info(f"[9PSB] Authentication successful using endpoint: {endpoint}")
                        self._cache_token(token, expires_in)
                        return token
                    else:
                        last_error = "No access token in response"
                else:
                    message = data.get('message', 'Authentication failed')
                    logger.warning(f"[9PSB] Auth failed at {endpoint}: {message}")
                    last_error = f"Code {data.get('code')}: {message}"
                    
            except requests.RequestException as e:
                logger.warning(f"[9PSB] Network error at {endpoint}: {str(e)}")
                last_error = f"Network error: {str(e)}"
                continue
            except json.JSONDecodeError:
                logger.warning(f"[9PSB] Invalid JSON response from {endpoint}")
                last_error = "Invalid JSON response"
                continue
        
        error_msg = f"All authentication endpoints failed. Last error: {last_error}"
        logger.error(f"[9PSB] {error_msg}")
        raise Exception(f"❌ Authentication failed: {last_error}")
    
    def _make_authenticated_request(self, method, endpoint, payload=None, retry_auth=True):
        """Make authenticated request with automatic token refresh"""
        token = self.authenticate()
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            if method.upper() == "POST":
                response = requests.post(url, json=payload, headers=headers, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            
            # Handle 401 with retry
            if response.status_code == 401 and retry_auth:
                logger.warning("[9PSB] Token expired, retrying with fresh token")
                cache.delete("psb_access_token")  # Clear cached token
                self._token = None
                self._token_expires_at = None
                return self._make_authenticated_request(method, endpoint, payload, retry_auth=False)
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    # ==========================================================
    # 🏦 VIRTUAL ACCOUNT CREATION (FIXED PARAMETER HANDLING)
    # ==========================================================
    
    def create_virtual_account(self, customer_data=None, **kwargs):
        """
        Create virtual account with flexible parameter handling
        
        FIXED: Supports both parameter styles:
        - create_virtual_account(customer_name="John", customer_id=1, ...)
        - create_virtual_account({'name': 'John', 'customer_id': 1, ...})
        """
        if not getattr(settings, 'PSB_ENABLED', True):
            raise Exception("9PSB service is disabled in settings")
        
        # FIXED: Handle both calling conventions
        if customer_data is None:
            # Called with individual kwargs
            customer_data = {
                'name': kwargs.get('customer_name', ''),
                'customer_id': kwargs.get('customer_id'),
                'phone': kwargs.get('phone_number', ''),
                'email': kwargs.get('email', '')
            }
        else:
            # Called with dictionary, merge with any kwargs
            if 'name' not in customer_data and 'customer_name' in kwargs:
                customer_data['name'] = kwargs['customer_name']
            if 'customer_id' not in customer_data and 'customer_id' in kwargs:
                customer_data['customer_id'] = kwargs['customer_id']
            if 'phone' not in customer_data and 'phone_number' in kwargs:
                customer_data['phone'] = kwargs['phone_number']
            if 'email' not in customer_data and 'email' in kwargs:
                customer_data['email'] = kwargs['email']
        
        # Generate unique reference
        reference = f"VA{datetime.now().strftime('%Y%m%d%H%M%S')}{customer_data.get('customer_id', '')}"
        
        # Prepare payload for virtual account creation
        payload = {
            "transaction": {"reference": reference},
            "order": {
                "amount": 0,  # Static account
                "currency": self.currency,
                "description": f"Virtual Account for {customer_data.get('name', '')}".strip(),
                "country": self.country,
                "amounttype": "ANY"  # Allows any amount
            },
            "customer": {
                "account": {
                    "name": customer_data.get('name', ''),
                    "type": "STATIC"
                }
            }
        }
        
        # FIXED: Use correct virtual account endpoints for iva-api/v1 base URL
        va_endpoints = [
            "/merchant/virtualaccount/create",  # Primary endpoint for iva-api/v1
            "/virtualaccount/create"  # Alternative
        ]
        
        last_error = None
        for endpoint in va_endpoints:
            try:
                logger.info(f"[9PSB] Creating virtual account using endpoint: {endpoint}")
                data = self._make_authenticated_request("POST", endpoint, payload)
                
                if data.get("code") == "00":
                    # Parse response
                    customer_account = data.get("customer", {}).get("account", {})
                    bank_info = data.get("bank", {})
                    
                    account_number = customer_account.get("number")
                    account_name = customer_account.get("name")
                    bank_name = bank_info.get("name") or customer_account.get("bank") or "9PSB"
                    bank_code = bank_info.get("code") or customer_account.get("bank_code") or "120001"
                    
                    if account_number:
                        logger.info(f"[9PSB] Virtual account created: {account_number}")
                        
                        # Update customer record if customer_id provided
                        if customer_data.get('customer_id'):
                            try:
                                customer = Customer.objects.get(id=customer_data['customer_id'])
                                customer.wallet_account = account_number
                                customer.bank_name = bank_name
                                customer.bank_code = bank_code
                                customer.save(update_fields=["wallet_account", "bank_name", "bank_code"])
                                logger.info(f"[9PSB] Updated customer {customer_data['customer_id']} with virtual account")
                            except Customer.DoesNotExist:
                                logger.warning(f"[9PSB] Customer {customer_data['customer_id']} not found for update")
                        
                        return {
                            'success': True,
                            'virtual_account_number': account_number,
                            'account_name': account_name,
                            'bank_name': bank_name,
                            'bank_code': bank_code,
                            'transaction_reference': reference,
                            'response_data': data
                        }
                    else:
                        last_error = "No account number in response"
                else:
                    last_error = data.get('message', 'Virtual account creation failed')
                    
            except Exception as e:
                logger.warning(f"[9PSB] VA creation failed at {endpoint}: {str(e)}")
                last_error = str(e)
                continue
        
        logger.error(f"[9PSB] All virtual account endpoints failed: {last_error}")
        return {
            'success': False,
            'error': f'Virtual account creation failed: {last_error}'
        }
    
    # ==========================================================
    # 👤 ACCOUNT VALIDATION
    # ==========================================================
    
    def validate_account(self, account_number: str, bank_code: str):
        """Validate bank account via 9PSB API"""
        payload = {
            "customer": {
                "account": {
                    "number": account_number,
                    "bank": bank_code
                }
            }
        }
        
        data = self._make_authenticated_request("POST", "/merchant/account/enquiry", payload)
        
        if data.get("code") != "00":
            raise Exception(f"❌ Account validation failed: {data.get('message')}")
        
        account_info = data.get("customer", {}).get("account", {})
        account_name = account_info.get("name") or data.get("account_name")
        
        return {
            "account_name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "valid": True,
            "full_response": data
        }
    
    # ==========================================================
    # 🏦 BANK LIST MANAGEMENT
    # ==========================================================
    
    def fetch_bank_list(self):
        """Fetch list of supported banks from 9PSB"""
        data = self._make_authenticated_request("POST", "/merchant/transfer/getbanks")
        
        if data.get("code") != "00":
            raise Exception(f"❌ Failed to fetch bank list: {data.get('message')}")
        
        banks = data.get("BankList", [])
        logger.info(f"[9PSB] Fetched {len(banks)} banks from API")
        
        return banks
    
    def update_bank_list(self):
        """Fetch banks and update local database"""
        banks = self.fetch_bank_list()
        
        # Try to import PsbBank model, create if doesn't exist
        try:
            from ninepsb.models import PsbBank
        except ImportError:
            logger.warning("PsbBank model not found, skipping database update")
            return banks
        
        count = 0
        for bank in banks:
            PsbBank.objects.update_or_create(
                bank_code=bank.get("BankCode"),
                defaults={
                    "bank_name": bank.get("BankName"),
                    "bank_long_code": bank.get("BankLongCode"),
                    "active": True,
                },
            )
            count += 1
        
        logger.info(f"[9PSB] Updated {count} banks in database")
        return banks
    
    # ==========================================================
    # 💰 FUND TRANSFER
    # ==========================================================
    
    def _generate_transfer_hash(self, sender_account, beneficiary_account, bank_code, amount, reference):
        """Generate SHA512 hash for 9PSB transfer"""
        raw = f"{self.private_key}{sender_account}{beneficiary_account}{bank_code}{format(amount, '.2f')}{reference}"
        return hashlib.sha512(raw.encode("utf-8")).hexdigest().upper()
    
    def fund_transfer(self, sender_name, sender_account, beneficiary_name, beneficiary_account, 
                     bank_code, amount, description="Wallet Transfer"):
        """Perform fund transfer via 9PSB"""
        reference = f"FT{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"
        
        hash_value = self._generate_transfer_hash(
            sender_account, beneficiary_account, bank_code, amount, reference
        )
        
        payload = {
            "transaction": {"reference": reference},
            "order": {
                "amount": float(amount),
                "description": description,
                "currency": self.currency,
                "country": self.country
            },
            "customer": {
                "account": {
                    "number": beneficiary_account,
                    "bank": bank_code,
                    "name": beneficiary_name,
                    "senderaccountnumber": sender_account,
                    "sendername": sender_name
                }
            },
            "hash": hash_value
        }
        
        data = self._make_authenticated_request("POST", "/merchant/account/transfer", payload)
        
        if data.get("code") != "00":
            raise Exception(f"❌ Fund transfer failed: {data.get('message')}")
        
        logger.info(f"[9PSB] Fund transfer successful: {reference}")
        return data
    
    def check_transfer_status(self, reference, linking_reference=None, external_reference=None):
        """Check status of fund transfer"""
        params = {
            "reference": reference,
            "linkingreference": linking_reference or "",
            "externalreference": external_reference or ""
        }
        
        # Use GET request with params for status check
        url = f"{self.base_url}/merchant/account/transfer/status"
        headers = {"Authorization": f"Bearer {self.authenticate()}"}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.json()
    
    # ==========================================================
    # 🛠️ UTILITY METHODS
    # ==========================================================
    
    def _normalize_phone(self, phone):
        """Normalize phone number to Nigerian format"""
        if not phone:
            return None
        
        phone = ''.join(filter(str.isdigit, phone))
        
        if phone.startswith('234'):
            return phone
        elif phone.startswith('0'):
            return '234' + phone[1:]
        elif len(phone) == 10:
            return '234' + phone
        else:
            return '234' + phone
    
    def health_check(self):
        """Check if 9PSB service is accessible"""
        try:
            token = self.authenticate()
            return {
                'status': 'healthy',
                'authenticated': bool(token),
                'base_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'base_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }

# ==========================================================
# FUNCTIONAL INTERFACE (backward compatibility)
# ==========================================================

# Initialize service instance
enhanced_psb_service = Enhanced9PSBService()

# Functional wrappers for backward compatibility
def psb_authenticate():
    """Authenticate with 9PSB and return token"""
    return enhanced_psb_service.authenticate()

def psb_create_virtual_account_for_customer(customer_id):
    """Create virtual account for customer (backward compatible)"""
    customer = Customer.objects.get(id=customer_id)
    result = enhanced_psb_service.create_virtual_account(
        customer_name=f"{customer.first_name} {customer.last_name}".strip(),
        customer_id=customer.id,
        phone_number=customer.phone_no,
        email=customer.email
    )
    
    if not result['success']:
        raise Exception(result['error'])
    
    return {
        "account_number": result['virtual_account_number'],
        "account_name": result['account_name'],
        "bank_name": result['bank_name'],
        "bank_code": result['bank_code']
    }

def psb_validate_account(account_number: str, bank_code: str):
    """Validate account (backward compatible)"""
    result = enhanced_psb_service.validate_account(account_number, bank_code)
    return {"account_name": result["account_name"], "full_response": result["full_response"]}

def fetch_and_update_psb_banks():
    """Fetch and update bank list (backward compatible)"""
    banks = enhanced_psb_service.update_bank_list()
    return f"✅ {len(banks)} banks updated successfully."

def psb_fund_transfer(sender_name, sender_account, beneficiary_name, beneficiary_account, 
                     bank_code, amount, description="Wallet Transfer"):
    """Fund transfer (backward compatible)"""
    return enhanced_psb_service.fund_transfer(
        sender_name, sender_account, beneficiary_name, beneficiary_account,
        bank_code, amount, description
    )

def psb_fund_transfer_status(reference, linking_reference=None, external_reference=None):
    """Check transfer status (backward compatible)"""
    return enhanced_psb_service.check_transfer_status(reference, linking_reference, external_reference)
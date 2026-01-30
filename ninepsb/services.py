import requests
import hashlib
from datetime import datetime
from django.conf import settings
from customers.models import Customer
from ninepsb.models import PsbBank

# ==========================================================
# 🔐 1. AUTHENTICATION
# ==========================================================
def psb_authenticate():
    """
    Authenticate with 9PSB and return a Bearer token.
    """
    url = f"{settings.PSB_BASE_URL}/merchant/authenticate"
    payload = {
        "publickey": settings.PSB_PUBLIC_KEY,
        "privatekey": settings.PSB_PRIVATE_KEY
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"❌ Network error during authentication: {str(e)}")

    data = response.json()
    if data.get("code") != "00":
        raise Exception(f"❌ Authentication failed: {data.get('message')}")

    return data["access_token"]

# ==========================================================
# 🏦 2. FETCH BANK LIST
# ==========================================================
def fetch_and_update_psb_banks():
    """
    Fetch bank list from 9PSB and update the local database.
    """
    token = psb_authenticate()
    url = f"{settings.PSB_BASE_URL}/merchant/transfer/getbanks"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    response = requests.post(url, headers=headers, timeout=30)
    data = response.json()

    if data.get("code") != "00":
        raise Exception(f"❌ Failed to fetch bank list: {data.get('message')}")

    count = 0
    for bank in data.get("BankList", []):
        PsbBank.objects.update_or_create(
            bank_code=bank.get("BankCode"),
            defaults={
                "bank_name": bank.get("BankName"),
                "bank_long_code": bank.get("BankLongCode"),
                "active": True,
            },
        )
        count += 1

    return f"✅ {count} banks updated successfully."

# ==========================================================
# 👤 3. ACCOUNT VALIDATION / ENQUIRY
# ==========================================================
def psb_validate_account(account_number: str, bank_code: str):
    """
    Validate a customer's bank account via 9PSB API.
    """
    token = psb_authenticate()
    url = f"{settings.PSB_BASE_URL}/merchant/account/enquiry"

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"customer": {"account": {"number": account_number, "bank": bank_code}}}

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    data = response.json()

    if data.get("code") != "00":
        raise Exception(f"❌ Account validation failed: {data.get('message')}")

    account_info = data.get("customer", {}).get("account", {})
    return {"account_name": account_info.get("name"), "full_response": data}

# ==========================================================
# 💳 4. FUND TRANSFER
# ==========================================================
def generate_psb_transfer_hash(private_key, sender_account, beneficiary_account, bank_code, amount, reference):
    """Generate SHA512 hash for 9PSB transfer."""
    raw = f"{private_key}{sender_account}{beneficiary_account}{bank_code}{format(amount, '.2f')}{reference}"
    return hashlib.sha512(raw.encode("utf-8")).hexdigest().upper()

def psb_fund_transfer(sender_name, sender_account, beneficiary_name, beneficiary_account, bank_code, amount, description="Wallet Transfer"):
    """Perform fund transfer via 9PSB."""
    token = psb_authenticate()
    reference = f"FT{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"

    hash_value = generate_psb_transfer_hash(
        settings.PSB_PRIVATE_KEY,
        sender_account,
        beneficiary_account,
        bank_code,
        amount,
        reference
    )

    url = f"{settings.PSB_BASE_URL}/merchant/account/transfer"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {
        "transaction": {"reference": reference},
        "order": {
            "amount": float(amount),
            "description": description,
            "currency": "NGN",
            "country": "NGA"
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

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    data = response.json()

    if data.get("code") != "00":
        raise Exception(f"❌ Fund transfer failed: {data.get('message')}")

    return data

# ==========================================================
# 🔎 5. FUND TRANSFER STATUS
# ==========================================================
def psb_fund_transfer_status(reference, linking_reference=None, external_reference=None):
    token = psb_authenticate()
    params = {
        "reference": reference,
        "linkingreference": linking_reference or "",
        "externalreference": external_reference or ""
    }
    url = f"{settings.PSB_BASE_URL}/merchant/account/transfer/status"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(url, headers=headers, params=params, timeout=30)
    data = response.json()
    return data

# ==========================================================
# 🏦 6. CREATE VIRTUAL ACCOUNT
# ==========================================================
def psb_create_virtual_account_for_customer(customer_id):
    customer = Customer.objects.get(id=customer_id)
    token = psb_authenticate()
    url = f"{settings.PSB_BASE_URL}/iva-api/v1/merchant/virtualaccount/create"

    payload = {
        "transaction": {"reference": f"VA{datetime.now().strftime('%Y%m%d%H%M%S')}{customer.id}"},
        "order": {
            "amount": 100,
            "currency": "NGN",
            "description": "Virtual Account Creation",
            "country": "NGA",
            "amounttype": "EXACT"
        },
        "customer": {"account": {"name": f"{customer.first_name} {customer.last_name}".strip(), "type": "STATIC"}}
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    data = response.json()

    if data.get("code") != "00":
        raise Exception(f"❌ Virtual Account creation failed: {data.get('message')}")

    account_info = data.get("customer", {}).get("account", {})
    account_number = account_info.get("number")
    account_name = account_info.get("name")
    bank_name = account_info.get("bank")
    bank_code = account_info.get("bank_code") or ""

    if account_number:
        customer.wallet_account = account_number
        customer.bank_name = bank_name
        customer.bank_code = bank_code
        customer.save(update_fields=["wallet_account", "bank_name", "bank_code"])

    return {"account_number": account_number, "account_name": account_name, "bank_name": bank_name, "bank_code": bank_code}

# ==========================================================
# 🧾 7. PSBService CLASS (optional OOP wrapper)
# ==========================================================
# ninepsb/services.py
import hashlib
import json
import requests
from django.conf import settings
from django.core.cache import cache  # Optional: cache token to avoid re-authenticating every time


class PSBService:
    def __init__(self):
        self.public_key = settings.PSB_PUBLIC_KEY
        self.private_key = settings.PSB_PRIVATE_KEY
        self.base_url = settings.PSB_BASE_URL
        self._token = None

    def _get_token(self):
        """Get or reuse a cached authentication token."""
        if self._token:
            return self._token

        # Optional: use Django cache to reduce auth calls
        cache_key = "psb_access_token"
        token = cache.get(cache_key)
        if token:
            self._token = token
            return token

        url = f"{self.base_url}/merchant/authenticate"
        payload = {
            "publickey": self.public_key,
            "privatekey": self.private_key
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise Exception(f"Network error during authentication: {str(e)}")
        except ValueError:
            raise Exception("Invalid JSON response from authentication endpoint.")

        if data.get("code") != "00":
            raise Exception(f"Authentication failed: {data.get('message', 'Invalid credentials')}")

        token = data.get("access_token")
        if not token:
            raise Exception("Authentication succeeded but no access token returned.")

        # Cache token for 55 minutes (assuming 1-hour expiry)
        cache.set(cache_key, token, timeout=55 * 60)
        self._token = token
        return token

    def _make_request(self, method, endpoint, payload=None):
        """Make an authenticated request to 9PSB."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_token()}"
        }

        try:
            if method.upper() == "POST":
                response = requests.post(url, json=payload, headers=headers, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")

    def account_enquiry(self, account_number: str, bank_code: str):
        """Validate account using 9PSB (requires auth token)."""
        payload = {
            "customer": {
                "account": {
                    "number": account_number,
                    "bank": bank_code
                }
            }
        }
        data = self._make_request("POST", "/merchant/account/enquiry", payload)

        if data.get("code") != "00":
            raise Exception(data.get("message", "Account enquiry failed"))

        account_name = (
            data.get("customer", {})
            .get("account", {})
            .get("name")
            or data.get("account_name")
        )
        return {"account_name": account_name, "raw": data}

    def fund_transfer(
        self,
        reference: str,
        amount: float,
        description: str,
        sender_account: str,
        sender_name: str,
        recipient_account: str,
        recipient_name: str,
        recipient_bank: str,
    ):
        """Perform fund transfer (requires auth token + hash)."""
        # Generate hash as per 9PSB spec (confirm format with docs)
        # Based on your working function, hash uses: private_key + sender + recipient + bank + amount + ref
        raw_hash = f"{self.private_key}{sender_account}{recipient_account}{recipient_bank}{format(amount, '.2f')}{reference}"
        hash_value = hashlib.sha512(raw_hash.encode()).hexdigest().upper()

        payload = {
            "transaction": {"reference": reference},
            "order": {
                "amount": float(amount),
                "description": description,
                "currency": getattr(settings, 'PSB_CURRENCY', 'NGN'),
                "country": getattr(settings, 'PSB_COUNTRY', 'NG'),
            },
            "customer": {
                "account": {
                    "number": recipient_account,
                    "bank": recipient_bank,
                    "name": recipient_name,
                    "senderaccountnumber": sender_account,
                    "sendername": sender_name,
                }
            },
            "hash": hash_value
        }

        data = self._make_request("POST", "/merchant/account/transfer", payload)

        if data.get("code") != "00":
            raise Exception(data.get("message", "Fund transfer failed."))

        return data


# ==========================================================
# 🏦 8. WAAS SERVICE CLASS (Wallet as a Service)
# ==========================================================
class WAASService:
    """
    9PSB Wallet as a Service (WAAS) API Integration.
    Used for merchant wallet operations.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'NINEPSB_API_BASE', 'http://102.216.128.75:9090/waas/api/v1')
        self.username = getattr(settings, 'NINEPSB_USERNAME', '')
        self.password = getattr(settings, 'NINEPSB_PASSWORD', '')
        self.client_id = getattr(settings, 'NINEPSB_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'NINEPSB_CLIENT_SECRET', '')
        self.timeout = getattr(settings, 'NINEPSB_API_TIMEOUT', 30)
        self._token = None
    
    def _get_token(self):
        """Authenticate with WAAS API and get access token."""
        if self._token:
            return self._token
        
        cache_key = "waas_access_token"
        token = cache.get(cache_key)
        if token:
            self._token = token
            return token
        
        url = f"{self.base_url}/authenticate"
        payload = {
            "username": self.username,
            "password": self.password,
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise Exception(f"WAAS authentication network error: {str(e)}")
        except ValueError:
            raise Exception("Invalid JSON response from WAAS authentication.")
        
        # Handle different response formats - check for success indicators
        status = data.get("status", "").upper()
        message = data.get("message", "").lower()
        
        # Check if authentication was successful (handle various response formats)
        is_success = (
            status == "SUCCESS" or
            status == "SUCCESSFUL" or
            message == "successful" or
            message == "success" or
            "successful" in message
        )
        
        if not is_success:
            raise Exception(f"WAAS authentication failed: {data.get('message', 'Unknown error')}")
        
        # Try different field names for access token
        token = data.get("accessToken") or data.get("access_token") or data.get("token")
        if not token:
            raise Exception(f"WAAS authentication succeeded but no access token returned. Response: {data}")
        
        # Cache token for 55 minutes
        expires_in = data.get("expiresIn", 3600)
        cache.set(cache_key, token, timeout=min(expires_in - 300, 3300))
        self._token = token
        return token
    
    def _make_request(self, method, endpoint, payload=None):
        """Make authenticated request to WAAS API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_token()}"
        }
        
        try:
            if method.upper() == "POST":
                response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            else:
                response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"WAAS API request failed: {str(e)}")
    
    def open_wallet(self, merchant_data: dict) -> dict:
        """
        Open a new 9PSB wallet for a merchant.
        
        Args:
            merchant_data: dict containing:
                - transactionTrackingRef: Unique reference
                - lastName: Last name
                - otherNames: Other names
                - phoneNo: Phone number
                - gender: 0 (Male) or 1 (Female)
                - dateOfBirth: Date in dd/MM/yyyy format
                - address: Address
                - bvn: Bank Verification Number (optional if NIN provided)
                - nin: National ID Number (optional if BVN provided)
                - ninUserId: NIN User ID (required if NIN provided)
                - email: Email address (optional)
        
        Returns:
            dict with wallet account details
        """
        payload = {
            "transactionTrackingRef": merchant_data.get("transactionTrackingRef"),
            "lastName": merchant_data.get("lastName"),
            "otherNames": merchant_data.get("otherNames"),
            "phoneNo": merchant_data.get("phoneNo"),
            "gender": int(merchant_data.get("gender", 0)),
            "dateOfBirth": merchant_data.get("dateOfBirth"),
            "address": merchant_data.get("address"),
        }
        
        # Add optional fields
        if merchant_data.get("bvn"):
            payload["bvn"] = merchant_data["bvn"]
        
        if merchant_data.get("nin"):
            payload["nationalIdentityNo"] = merchant_data["nin"]
            if merchant_data.get("ninUserId"):
                payload["ninUserId"] = merchant_data["ninUserId"]
        
        if merchant_data.get("email"):
            payload["email"] = merchant_data["email"]
        
        if merchant_data.get("accountName"):
            payload["accountName"] = merchant_data["accountName"]
        
        if merchant_data.get("placeOfBirth"):
            payload["placeOfBirth"] = merchant_data["placeOfBirth"]
        
        data = self._make_request("POST", "/open_wallet", payload)
        
        # Handle different response formats
        status = data.get("status", "").upper()
        message = data.get("message", "").lower()
        
        is_success = (
            status == "SUCCESS" or
            status == "SUCCESSFUL" or
            "successful" in message or
            "success" in message
        )
        
        if not is_success:
            raise Exception(f"Wallet opening failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def wallet_enquiry(self, account_no: str) -> dict:
        """Fetch wallet details by account number."""
        payload = {"accountNo": account_no}
        data = self._make_request("POST", "/wallet_enquiry", payload)
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Wallet enquiry failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def wallet_status(self, account_no: str) -> dict:
        """Fetch wallet status by account number."""
        payload = {"accountNo": account_no}
        data = self._make_request("POST", "/wallet_status", payload)
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Wallet status check failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def change_wallet_status(self, account_number: str, new_status: str) -> dict:
        """
        Change wallet status.
        
        Args:
            account_number: Wallet account number
            new_status: ACTIVE or SUSPENDED
        """
        payload = {
            "accountNumber": account_number,
            "accountStatus": new_status
        }
        data = self._make_request("POST", "/change_wallet_status", payload)
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Wallet status change failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def debit_wallet(self, account_no: str, amount: str, transaction_id: str, 
                     narration: str, merchant_fee: dict = None) -> dict:
        """Debit a wallet account."""
        payload = {
            "accountNo": account_no,
            "totalAmount": str(amount),
            "transactionId": transaction_id,
            "narration": narration,
            "merchant": merchant_fee or {"isFee": False}
        }
        data = self._make_request("POST", "/debit/transfer", payload)
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Wallet debit failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def credit_wallet(self, account_no: str, amount: str, transaction_id: str,
                      narration: str, merchant_fee: dict = None) -> dict:
        """Credit a wallet account."""
        payload = {
            "accountNo": account_no,
            "totalAmount": str(amount),
            "transactionId": transaction_id,
            "narration": narration,
            "merchant": merchant_fee or {"isFee": False}
        }
        data = self._make_request("POST", "/credit/transfer", payload)
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Wallet credit failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def wallet_transactions(self, account_number: str, from_date: str, 
                           to_date: str, number_of_items: int = 50) -> dict:
        """Fetch wallet transaction history."""
        payload = {
            "accountNumber": account_number,
            "fromDate": from_date,
            "toDate": to_date,
            "numberOfItems": str(number_of_items)
        }
        data = self._make_request("POST", "/wallet_transactions", payload)
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Wallet transactions fetch failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def transaction_status(self, transaction_id: str, amount: int, 
                          transaction_type: str, transaction_date: str,
                          account_no: str) -> dict:
        """Query transaction status."""
        payload = {
            "transactionId": transaction_id,
            "amount": amount,
            "transactionType": transaction_type,
            "transactionDate": transaction_date,
            "accountNo": account_no
        }
        data = self._make_request("POST", "/wallet_requery", payload)
        return data
    
    def get_banks(self) -> dict:
        """Fetch list of all banks."""
        data = self._make_request("GET", "/get_banks")
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Get banks failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def transfer_to_other_bank(self, transaction_ref: str, amount: float,
                               sender_account: str, sender_name: str,
                               recipient_account: str, recipient_name: str,
                               recipient_bank_code: str, narration: str) -> dict:
        """Transfer from wallet to other bank."""
        payload = {
            "transaction": {"reference": transaction_ref},
            "order": {
                "amount": float(amount),
                "currency": "NGN",
                "country": "NGA"
            },
            "customer": {
                "account": {
                    "number": recipient_account,
                    "bank": recipient_bank_code,
                    "name": recipient_name,
                    "senderaccountnumber": sender_account,
                    "sendername": sender_name
                }
            },
            "merchant": {},
            "transactionType": "OTHER_BANKS",
            "narration": narration
        }
        data = self._make_request("POST", "/wallet_other_banks", payload)
        return data
    
    def other_bank_enquiry(self, account_number: str, bank_code: str) -> dict:
        """Verify account details of other bank's account."""
        payload = {
            "customer": {
                "account": {
                    "number": account_number,
                    "bank": bank_code
                }
            }
        }
        data = self._make_request("POST", "/other_banks_enquiry", payload)
        
        if data.get("status") != "SUCCESS":
            raise Exception(f"Bank enquiry failed: {data.get('message', 'Unknown error')}")
        
        return data
    
    def get_wallet_by_bvn(self, bvn: str) -> dict:
        """Fetch wallet information using BVN."""
        payload = {"bvn": bvn}
        data = self._make_request("POST", "/get_wallet", payload)
        return data


# Helper function for merchant wallet creation
def create_merchant_wallet(merchant) -> dict:
    """
    Create a 9PSB wallet for a merchant.
    
    Args:
        merchant: Merchant model instance
    
    Returns:
        dict with wallet details
    """
    import logging
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    waas = WAASService()
    
    # Parse merchant name
    name_parts = merchant.merchant_name.split()
    last_name = name_parts[-1] if name_parts else "Merchant"
    other_names = " ".join(name_parts[:-1]) if len(name_parts) > 1 else "Merchant"
    
    # Format date of birth
    dob_formatted = merchant.date_of_birth.strftime("%d/%m/%Y") if merchant.date_of_birth else ""
    
    # Generate unique tracking reference
    tracking_ref = f"MRC{merchant.merchant_code}{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    wallet_data = {
        "transactionTrackingRef": tracking_ref,
        "lastName": last_name,
        "otherNames": other_names,
        "accountName": merchant.merchant_name,
        "phoneNo": merchant.business_phone,
        "gender": merchant.gender or "0",
        "dateOfBirth": dob_formatted,
        "address": merchant.address or merchant.business_address or "Nigeria",
        "email": merchant.business_email,
    }
    
    # Add BVN if available
    if merchant.bvn:
        wallet_data["bvn"] = merchant.bvn
    
    # Add NIN if available
    if merchant.nin:
        wallet_data["nin"] = merchant.nin
    
    logger.info(f"Creating wallet for merchant {merchant.merchant_id} with data: {wallet_data}")
    
    result = waas.open_wallet(wallet_data)
    
    logger.info(f"Wallet API response for merchant {merchant.merchant_id}: {result}")
    
    # Extract account details from response - handle various response formats
    account_data = result.get("data", {})
    
    # Try different possible field names for account number
    account_number = (
        account_data.get("accountNo") or 
        account_data.get("accountNumber") or
        account_data.get("account_number") or
        account_data.get("walletAccountNo") or
        result.get("accountNo") or
        result.get("accountNumber")
    )
    
    # Try different possible field names for account name
    account_name = (
        account_data.get("accountName") or
        account_data.get("account_name") or
        account_data.get("name") or
        result.get("accountName") or
        merchant.merchant_name
    )
    
    logger.info(f"Extracted account_number: {account_number}, account_name: {account_name}")
    
    return {
        "account_number": account_number,
        "account_name": account_name,
        "status": "active",
        "tier": account_data.get("tier") or result.get("tier") or "1",
        "message": result.get("message", "Wallet created successfully"),
        "raw_response": result
    }









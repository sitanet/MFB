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









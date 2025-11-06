"""
enhanced_psb_service.py

Unified 9PSB integration service:
- Authentication with caching
- Virtual account creation (static)
- Account validation
- Bank list management
- Fund transfer and status checks
- Robust logging + defensive parsing
"""

import json
import logging
import hashlib
import uuid
import requests
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

try:
    from customers.models import Customer
except Exception:
    Customer = None

logger = logging.getLogger(__name__)


class Enhanced9PSBService:
    """Unified 9PSB service class"""

    def __init__(self):
        self.public_key = getattr(settings, "PSB_PUBLIC_KEY", "")
        self.private_key = getattr(settings, "PSB_PRIVATE_KEY", "")
        self.base_url = getattr(settings, "PSB_BASE_URL", "https://baastest.9psb.com.ng/iva-api/v1")
        self.currency = getattr(settings, "PSB_CURRENCY", "NGN")
        self.country = getattr(settings, "PSB_COUNTRY", "NGA")
        self._token = None
        self._token_expires_at = None
        self.cache_key = "psb_access_token"
        self.enabled = getattr(settings, "PSB_ENABLED", True)

    # ----------------------------------------------------------------
    # AUTHENTICATION
    # ----------------------------------------------------------------
    def authenticate(self):
        """Authenticate with 9PSB and cache token"""
        cached = cache.get(self.cache_key)
        if cached:
            token = cached.get("token")
            expires_at = datetime.fromisoformat(cached.get("expires_at"))
            if datetime.now() < expires_at:
                self._token = token
                self._token_expires_at = expires_at
                logger.info("[9PSB] Using cached authentication token")
                return token

        payload = {"publickey": self.public_key, "privatekey": self.private_key}
        headers = {"Content-Type": "application/json"}

        url = f"{self.base_url}/merchant/virtualaccount/authenticate"
        try:
            logger.info(f"[9PSB] Authenticating via {url}")
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            data = resp.json()
            logger.debug(f"[9PSB] Auth response: {data}")

            if str(data.get("code")) == "00" and data.get("access_token"):
                token = data["access_token"]
                expires_in = int(data.get("expires_in", 3600))
                expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                cache.set(self.cache_key, {"token": token, "expires_at": expires_at.isoformat()}, expires_in - 60)
                self._token = token
                self._token_expires_at = expires_at
                logger.info("[9PSB] Authentication successful")
                return token
            else:
                msg = data.get("message", "Authentication failed")
                raise Exception(msg)
        except Exception as e:
            logger.error(f"[9PSB] Authentication error: {e}")
            raise

    # ----------------------------------------------------------------
    # INTERNAL REQUEST
    # ----------------------------------------------------------------
    def _make_authenticated_request(self, method, endpoint, payload=None):
        if not self.enabled:
            raise Exception("9PSB is disabled")

        token = self.authenticate()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"{self.base_url}{endpoint}"

        try:
            logger.info(f"[9PSB] {method} {url}")
            resp = requests.request(method, url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[9PSB] Request error: {e}")
            raise

    # ----------------------------------------------------------------
    # CREATE VIRTUAL ACCOUNT
    # ----------------------------------------------------------------
    def create_virtual_account(self, customer_data=None, **kwargs):
        """Create static virtual account for a customer"""
        if not self.enabled:
            raise Exception("9PSB is disabled")

        if not isinstance(customer_data, dict):
            customer_data = {}

        # normalize inputs
        customer_data.update(kwargs)
        name = customer_data.get("name") or customer_data.get("customer_name") or "Unnamed Customer"
        phone = customer_data.get("phone") or customer_data.get("phone_number")
        email = customer_data.get("email", f"noemail_{uuid.uuid4().hex[:5]}@financeflex.com")
        customer_id = customer_data.get("customer_id")

        reference = f"VA_{customer_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        payload = {
            "transaction": {"reference": reference},
            "order": {
                "amount": 0,
                "currency": self.currency,
                "country": self.country,
                "amounttype": "ANY",
                "description": f"Virtual Account for {name}"
            },
            "customer": {
                "account": {"name": name, "type": "STATIC"},
                "phone": phone,
                "email": email,
            }
        }

        try:
            data = self._make_authenticated_request("POST", "/merchant/virtualaccount/create", payload)
            logger.debug(f"[9PSB] VA create response: {json.dumps(data, indent=2)}")

            if str(data.get("code")) == "00":
                account_number = (
                    data.get("virtualAccountNumber")
                    or data.get("accountNumber")
                    or (data.get("customer") or {}).get("account", {}).get("number")
                )
                if account_number:
                    if Customer and customer_id:
                        try:
                            cust = Customer.objects.get(id=customer_id)
                            cust.wallet_account = account_number
                            cust.bank_name = "9PSB"
                            cust.bank_code = "120001"
                            cust.save(update_fields=["wallet_account", "bank_name", "bank_code"])
                        except Customer.DoesNotExist:
                            logger.warning(f"[9PSB] Customer {customer_id} not found")

                    return {
                        "success": True,
                        "virtual_account_number": account_number,
                        "bank_name": "9PSB",
                        "bank_code": "120001",
                        "transaction_reference": reference,
                    }
                else:
                    return {"success": False, "error": "Missing account number", "response_data": data}
            else:
                return {"success": False, "error": data.get("message", "Virtual account creation failed")}
        except Exception as e:
            logger.error(f"[9PSB] Virtual account creation error: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # VALIDATION / BANK LIST / TRANSFER (OPTIONAL)
    # ----------------------------------------------------------------
    def validate_account(self, account_number, bank_code):
        payload = {"customer": {"account": {"number": account_number, "bank": bank_code}}}
        data = self._make_authenticated_request("POST", "/merchant/account/enquiry", payload)
        if str(data.get("code")) == "00":
            return data
        raise Exception(data.get("message", "Validation failed"))

    def fetch_bank_list(self):
        data = self._make_authenticated_request("POST", "/merchant/transfer/getbanks")
        return data.get("BankList") or data.get("banks") or []

    def fund_transfer(self, sender_name, sender_account, beneficiary_name, beneficiary_account, bank_code, amount):
        reference = f"FT_{uuid.uuid4().hex[:8]}"
        raw = f"{self.private_key}{sender_account}{beneficiary_account}{bank_code}{float(amount):.2f}{reference}"
        hash_value = hashlib.sha512(raw.encode()).hexdigest().upper()

        payload = {
            "transaction": {"reference": reference},
            "order": {"amount": float(amount), "currency": self.currency, "country": self.country},
            "customer": {
                "account": {
                    "number": beneficiary_account,
                    "bank": bank_code,
                    "name": beneficiary_name,
                    "senderaccountnumber": sender_account,
                    "sendername": sender_name
                }
            },
            "hash": hash_value,
        }

        return self._make_authenticated_request("POST", "/merchant/account/transfer", payload)


# Singleton instance
enhanced_psb_service = Enhanced9PSBService()

"""
enhanced_psb_service.py

Full-featured 9PSB integration service for:
- Authentication with caching
- Virtual account creation (flexible parameters)
- Account validation
- Bank list management
- Fund transfer and status checks
- Robust logging and defensive parsing
"""

import json
import logging
import hashlib
import uuid
import requests
from datetime import datetime, timedelta

# Django imports
from django.conf import settings
from django.core.cache import cache
from django.db import transaction

# Optional local model imports
try:
    from customers.models import Customer
except Exception:
    Customer = None

logger = logging.getLogger(__name__)


class Enhanced9PSBService:
    """
    Comprehensive 9PSB service with improved error handling and flexible inputs.
    """

    def __init__(self):
        # Keys and urls come from Django settings; sensible defaults included for dev/testing
        self.public_key = getattr(settings, "PSB_PUBLIC_KEY", "")
        self.private_key = getattr(settings, "PSB_PRIVATE_KEY", "")
        # Base URL should point to the API root (no trailing slash)
        self.base_url = getattr(settings, "PSB_BASE_URL", "https://baastest.9psb.com.ng/iva-api/v1")
        self.currency = getattr(settings, "PSB_CURRENCY", "NGN")
        self.country = getattr(settings, "PSB_COUNTRY", "NGA")
        self._token = None
        self._token_expires_at = None
        self.cache_key = getattr(settings, "PSB_CACHE_KEY", "psb_access_token")
        # Optional toggle to disable PSB in non-production
        self.enabled = getattr(settings, "PSB_ENABLED", True)

    # -------------------------
    # Token helpers / caching
    # -------------------------
    def _is_token_valid(self):
        if not self._token or not self._token_expires_at:
            return False
        # Buffer so we refresh early
        buffer_time = datetime.now() + timedelta(minutes=5)
        return self._token_expires_at > buffer_time

    def _get_cached_token(self):
        cached = cache.get(self.cache_key)
        if not cached:
            return None
        try:
            token = cached.get("token")
            expires_at = cached.get("expires_at")
            # If stored as ISO string, parse
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            self._token = token
            self._token_expires_at = expires_at
            if self._is_token_valid():
                return self._token
            # else treat as invalid
            return None
        except Exception:
            return None

    def _cache_token(self, token, expires_in=3600):
        # expires_in is seconds, store with 5 min buffer
        # We set stored expiry slightly earlier to force refresh before real expiry
        buffer_seconds = 300
        store_timeout = max(expires_in - buffer_seconds, 60)
        expires_at = datetime.now() + timedelta(seconds=expires_in - buffer_seconds)
        cache_data = {"token": token, "expires_at": expires_at.isoformat()}
        try:
            cache.set(self.cache_key, cache_data, timeout=store_timeout)
        except Exception:
            logger.warning("[9PSB] Could not cache token; continuing without cache.")
        self._token = token
        self._token_expires_at = expires_at

    # -------------------------
    # Authentication
    # -------------------------
    def authenticate(self):
        """
        Authenticate with 9PSB.
        Returns access token or raises Exception on failure.
        """
        # Return cached if valid
        cached = self._get_cached_token()
        if cached:
            logger.info("[9PSB] Using cached authentication token")
            return cached

        if not self.public_key or not self.private_key:
            raise Exception("9PSB API keys not configured in settings")

        auth_endpoints = [
            "/merchant/virtualaccount/authenticate",
            "/merchant/authenticate",
            "/authenticate",
        ]

        headers = {"Content-Type": "application/json"}
        payload = {"publickey": self.public_key, "privatekey": self.private_key}

        last_error = None
        for ep in auth_endpoints:
            url = f"{self.base_url}{ep}"
            try:
                logger.info(f"[9PSB] Authenticating using endpoint: {url}")
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                # If HTML response (e.g., 404 page), skip
                content_type = resp.headers.get("content-type", "").lower()
                if "text/html" in content_type:
                    last_error = f"HTML response from {url} (likely 404)"
                    logger.warning(f"[9PSB] {last_error}")
                    continue

                resp.raise_for_status()
                data = resp.json()
                logger.debug(f"[9PSB] Auth response: {json.dumps(data, indent=2)}")

                # Accept code==00 as success even if access_token key name varies
                if str(data.get("code")) == "00":
                    token = data.get("access_token") or data.get("token") or data.get("accessToken")
                    expires_in = int(data.get("expires_in", data.get("expiresIn", 3600)))
                    if token:
                        self._cache_token(token, expires_in)
                        logger.info(f"[9PSB] Authentication successful via {ep}")
                        return token
                    else:
                        # If code=00 but token missing, still continue to other endpoints or fail
                        last_error = {"code": data.get("code"), "message": "Auth success but missing token", "data": data}
                        logger.warning(f"[9PSB] Auth returned code=00 but no token: {json.dumps(data)}")
                        continue
                else:
                    last_error = data.get("message") or f"Auth failed with code {data.get('code')}"
                    logger.warning(f"[9PSB] Auth failed at {ep}: {last_error}")
                    continue

            except requests.RequestException as e:
                last_error = f"Network error at {ep}: {str(e)}"
                logger.warning(f"[9PSB] {last_error}")
                continue
            except ValueError:
                last_error = f"Invalid JSON from {ep}"
                logger.warning(f"[9PSB] {last_error}")
                continue

        err_msg = f"All authentication endpoints failed. Last error: {last_error}"
        logger.error(f"[9PSB] {err_msg}")
        raise Exception(err_msg)

    # -------------------------
    # Internal authenticated request
    # -------------------------
    def _make_authenticated_request(self, method, endpoint_or_url, payload=None, params=None, retry_auth=True):
        """
        method: 'POST' or 'GET'
        endpoint_or_url: full URL or path starting with '/'
        """
        if not self.enabled:
            raise Exception("9PSB service is disabled in settings")

        # Build full url if necessary
        if endpoint_or_url.startswith("http://") or endpoint_or_url.startswith("https://"):
            url = endpoint_or_url
        else:
            url = f"{self.base_url}{endpoint_or_url}"

        # Ensure token
        try:
            token = self.authenticate()
        except Exception as e:
            raise Exception(f"Authentication failed before request: {str(e)}")

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

        try:
            logger.info(f"[9PSB] {method} {url}")
            if method.upper() == "POST":
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
            else:
                resp = requests.get(url, headers=headers, params=params, timeout=30)

            # If 401, try to refresh once
            if resp.status_code == 401 and retry_auth:
                logger.warning("[9PSB] 401 Unauthorized - attempting token refresh")
                try:
                    cache.delete(self.cache_key)
                except Exception:
                    pass
                self._token = None
                self._token_expires_at = None
                # Re-authenticate and retry once
                new_token = self.authenticate()
                headers["Authorization"] = f"Bearer {new_token}"
                if method.upper() == "POST":
                    resp = requests.post(url, json=payload, headers=headers, timeout=30)
                else:
                    resp = requests.get(url, headers=headers, params=params, timeout=30)

            resp.raise_for_status()
            # Some endpoints return non-json or wrapped content; handle gracefully
            try:
                data = resp.json()
            except ValueError:
                # If not JSON, return raw text in a dict
                data = {"raw_text": resp.text, "status_code": resp.status_code}
            return data

        except requests.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except Exception as e:
            raise

    # -------------------------
    # Virtual account creation
    # -------------------------
    def create_virtual_account(self, customer_data=None, **kwargs):
        """
        Create virtual account with flexible parameter handling.

        Usage:
          create_virtual_account(customer_name="John Doe", customer_id=1, phone_number="234...", email="...")
          or
          create_virtual_account({'name': 'John Doe', 'customer_id': 1, 'phone': '080...', 'email': '...'})
        """
        if not self.enabled:
            raise Exception("9PSB service is disabled in settings")

        # Normalize parameters to internal dict
        if customer_data is None:
            customer_data = {
                "name": kwargs.get("customer_name", ""),
                "customer_id": kwargs.get("customer_id"),
                "phone": kwargs.get("phone_number") or kwargs.get("phone"),
                "email": kwargs.get("email", "")
            }
        else:
            # Merge kwargs if provided
            if isinstance(customer_data, dict):
                if "name" not in customer_data and "customer_name" in kwargs:
                    customer_data["name"] = kwargs["customer_name"]
                if "customer_id" not in customer_data and "customer_id" in kwargs:
                    customer_data["customer_id"] = kwargs["customer_id"]
                if "phone" not in customer_data and ("phone_number" in kwargs or "phone" in kwargs):
                    customer_data["phone"] = kwargs.get("phone_number") or kwargs.get("phone")
                if "email" not in customer_data and "email" in kwargs:
                    customer_data["email"] = kwargs["email"]
            else:
                # Not dict — try to coerce single str to name
                customer_data = {"name": str(customer_data)}

        # Build unique reference per docs style
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        reference = f"{timestamp}{customer_data.get('customer_id', '')}{uuid.uuid4().hex[:6]}"

        payload = {
            "transaction": {"reference": reference},
            "order": {
                "amount": 0,
                "currency": self.currency,
                "description": f"Virtual Account for {customer_data.get('name','')}".strip(),
                "country": self.country,
                "amounttype": "ANY"
            },
            "customer": {
                "account": {
                    "name": customer_data.get("name", ""),
                    "type": "STATIC"
                },
                # include contact fields if present
                "email": customer_data.get("email", ""),
                "phone": customer_data.get("phone", "")
            }
        }

        va_endpoints = [
            "/merchant/virtualaccount/create",
            "/merchant/virtual/create",
            "/virtualaccount/create",
        ]

        last_error = None
        for ep in va_endpoints:
            try:
                logger.info(f"[9PSB] Attempting VA create at endpoint: {ep}")
                data = self._make_authenticated_request("POST", ep, payload)
                logger.debug(f"[9PSB] VA raw response: {json.dumps(data, indent=2)}")

                # Handle success
                if str(data.get("code")) == "00":
                    # try multiple places for account info
                    customer_account = (
                        (data.get("customer") or {}).get("account", {})
                        or data.get("Account", {})
                        or data.get("customer_account", {})
                        or {}
                    )
                    bank_info = data.get("bank") or data.get("Bank") or {}
                    # possible fields
                    account_number = (
                        customer_account.get("number")
                        or customer_account.get("accountNumber")
                        or data.get("accountNumber")
                        or data.get("virtualAccountNumber")
                        or data.get("virtual_account")
                    )
                    account_name = (
                        customer_account.get("name")
                        or data.get("accountName")
                        or customer_data.get("name")
                    )
                    bank_name = bank_info.get("name") or data.get("bankName") or "9PSB"
                    bank_code = bank_info.get("code") or bank_info.get("BankCode") or data.get("bankCode") or "120001"

                    if account_number:
                        # Update customer model if provided
                        if customer_data.get("customer_id") and Customer:
                            try:
                                cust = Customer.objects.get(id=customer_data["customer_id"])
                                cust.wallet_account = account_number
                                cust.bank_name = bank_name
                                cust.bank_code = bank_code
                                cust.save(update_fields=["wallet_account", "bank_name", "bank_code"])
                                logger.info(f"[9PSB] Updated Customer {cust.id} with VA {account_number}")
                            except Customer.DoesNotExist:
                                logger.warning(f"[9PSB] Customer id {customer_data.get('customer_id')} not found to update VA")

                        return {
                            "success": True,
                            "virtual_account_number": account_number,
                            "account_name": account_name,
                            "bank_name": bank_name,
                            "bank_code": bank_code,
                            "transaction_reference": reference,
                            "response_data": data
                        }
                    else:
                        # Code 00 but missing account number — return informative failure
                        last_error = f"Success (code=00) but missing account number. Full response: {json.dumps(data)}"
                        logger.warning(f"[9PSB] {last_error}")
                        # Return partial info to caller so they can inspect response
                        return {
                            "success": False,
                            "error": "Success response but missing virtual account number",
                            "response_data": data
                        }

                else:
                    # Not success
                    msg = data.get("message") or data.get("msg") or "Virtual account creation failed"
                    last_error = f"API returned code {data.get('code')}: {msg}"
                    logger.warning(f"[9PSB] {last_error}")
                    # continue to try other endpoints
                    continue

            except Exception as e:
                logger.warning(f"[9PSB] VA creation failed at {ep}: {str(e)}")
                last_error = str(e)
                continue

        # All endpoints failed
        logger.error(f"[9PSB] All virtual account endpoints failed: {last_error}")
        return {"success": False, "error": last_error, "reference": reference}

    # -------------------------
    # Account validation
    # -------------------------
    def validate_account(self, account_number: str, bank_code: str):
        payload = {
            "customer": {
                "account": {
                    "number": account_number,
                    "bank": bank_code
                }
            }
        }

        try:
            data = self._make_authenticated_request("POST", "/merchant/account/enquiry", payload)
            logger.debug(f"[9PSB] Account enquiry response: {json.dumps(data, indent=2)}")
            if str(data.get("code")) != "00":
                raise Exception(f"Account validation failed: {data.get('message') or data}")
            account_info = (data.get("customer") or {}).get("account", {}) or {}
            account_name = account_info.get("name") or data.get("account_name") or data.get("accountName")
            return {
                "account_name": account_name,
                "account_number": account_number,
                "bank_code": bank_code,
                "valid": True,
                "full_response": data
            }
        except Exception as e:
            raise

    # -------------------------
    # Bank list
    # -------------------------
    def fetch_bank_list(self):
        try:
            data = self._make_authenticated_request("POST", "/merchant/transfer/getbanks")
            logger.debug(f"[9PSB] Bank list raw: {json.dumps(data, indent=2)}")
            if str(data.get("code")) != "00":
                raise Exception(f"Failed to fetch bank list: {data.get('message')}")
            banks = data.get("BankList") or data.get("banks") or []
            logger.info(f"[9PSB] Fetched {len(banks)} banks")
            return banks
        except Exception:
            raise

    def update_bank_list(self):
        banks = self.fetch_bank_list()
        try:
            from ninepsb.models import PsbBank
        except Exception:
            logger.warning("[9PSB] PsbBank model not found; returning banks without DB update")
            return banks

        count = 0
        for b in banks:
            code = b.get("BankCode") or b.get("bankCode") or b.get("code")
            name = b.get("BankName") or b.get("bankName") or b.get("name")
            long_code = b.get("BankLongCode") or b.get("bankLongCode") or ""
            if not code:
                continue
            PsbBank.objects.update_or_create(
                bank_code=code,
                defaults={"bank_name": name or code, "bank_long_code": long_code, "active": True}
            )
            count += 1
        logger.info(f"[9PSB] Updated {count} banks in DB")
        return banks

    # -------------------------
    # Fund transfer
    # -------------------------
    def _generate_transfer_hash(self, sender_account, beneficiary_account, bank_code, amount, reference):
        """
        Generate required SHA512 hash for secure fund transfer signature.
        Adjust ordering/concatenation to match PSB documentation.
        """
        raw = f"{self.private_key}{sender_account}{beneficiary_account}{bank_code}{format(float(amount), '.2f')}{reference}"
        return hashlib.sha512(raw.encode("utf-8")).hexdigest().upper()

    def fund_transfer(self, sender_name, sender_account, beneficiary_name, beneficiary_account, bank_code, amount, description="Wallet Transfer"):
        reference = f"FT{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"
        hash_value = self._generate_transfer_hash(sender_account, beneficiary_account, bank_code, amount, reference)

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

        try:
            data = self._make_authenticated_request("POST", "/merchant/account/transfer", payload)
            logger.debug(f"[9PSB] Transfer response: {json.dumps(data, indent=2)}")
            if str(data.get("code")) != "00":
                raise Exception(f"Fund transfer failed: {data.get('message')}")
            logger.info(f"[9PSB] Fund transfer initiated: {reference}")
            return data
        except Exception:
            raise

    def check_transfer_status(self, reference, linking_reference=None, external_reference=None):
        params = {
            "reference": reference,
            "linkingreference": linking_reference or "",
            "externalreference": external_reference or ""
        }
        try:
            # Some APIs use GET with params
            url = f"{self.base_url}/merchant/account/transfer/status"
            headers = {"Authorization": f"Bearer {self.authenticate()}"}
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise

    # -------------------------
    # Utilities
    # -------------------------
    def _normalize_phone(self, phone):
        if not phone:
            return None
        phone = "".join(filter(str.isdigit, str(phone)))
        if phone.startswith("234"):
            return phone
        if phone.startswith("0"):
            return "234" + phone[1:]
        if len(phone) == 10:
            return "234" + phone
        # default fallback
        return "234" + phone

    def health_check(self):
        try:
            token = self.authenticate()
            return {"status": "healthy", "authenticated": bool(token), "base_url": self.base_url, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "base_url": self.base_url, "timestamp": datetime.now().isoformat()}


# Singleton instance for import
enhanced_psb_service = Enhanced9PSBService()


# -------------------------
# Backward-compatible functional wrappers
# -------------------------
def psb_authenticate():
    return enhanced_psb_service.authenticate()


def psb_create_virtual_account_for_customer(customer_id):
    if Customer is None:
        raise Exception("Customer model not available")
    customer = Customer.objects.get(id=customer_id)
    result = enhanced_psb_service.create_virtual_account(
        {
            "name": f"{customer.first_name} {customer.last_name}".strip(),
            "customer_id": customer.id,
            "phone": getattr(customer, "phone_no", None) or getattr(customer, "phone", None),
            "email": customer.email
        }
    )
    if not result.get("success"):
        raise Exception(result.get("error") or "Virtual account creation failed")
    return {
        "account_number": result.get("virtual_account_number"),
        "account_name": result.get("account_name"),
        "bank_name": result.get("bank_name"),
        "bank_code": result.get("bank_code")
    }


def psb_validate_account(account_number: str, bank_code: str):
    res = enhanced_psb_service.validate_account(account_number, bank_code)
    return {"account_name": res["account_name"], "full_response": res["full_response"]}


def fetch_and_update_psb_banks():
    banks = enhanced_psb_service.update_bank_list()
    return f"✅ {len(banks)} banks updated successfully."


def psb_fund_transfer(sender_name, sender_account, beneficiary_name, beneficiary_account, bank_code, amount, description="Wallet Transfer"):
    return enhanced_psb_service.fund_transfer(sender_name, sender_account, beneficiary_name, beneficiary_account, bank_code, amount, description)


def psb_fund_transfer_status(reference, linking_reference=None, external_reference=None):
    return enhanced_psb_service.check_transfer_status(reference, linking_reference, external_reference)

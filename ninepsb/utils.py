import requests
import datetime
from django.conf import settings

def get_access_token():
    """Authenticate with 9PSB and return Bearer token."""
    url = f"{settings.PSB_BASE_URL}/merchant/virtualaccount/authenticate"
    payload = {
        "publickey": settings.PSB_PUBLIC_KEY,
        "privatekey": settings.PSB_PRIVATE_KEY
    }
    headers = {"Content-Type": "application/json"}

    print("🔹 AUTH URL:", url)
    print("🔹 AUTH PAYLOAD:", payload)

    response = requests.post(url, json=payload, headers=headers)
    print("🔹 AUTH STATUS:", response.status_code)
    print("🔹 AUTH TEXT:", response.text[:300])

    try:
        data = response.json()
    except ValueError:
        raise Exception(f"Invalid JSON response from 9PSB: {response.text[:200]}")

    if data.get("code") == "00":
        return data["access_token"]
    raise Exception(f"Auth failed: {data.get('message', 'Unknown error')}")


def create_virtual_account(name, amount=100.0, account_type="STATIC", amount_type="EXACT"):
    """Create a virtual account using 9PSB API."""
    token = get_access_token()
    url = f"{settings.PSB_BASE_URL}/merchant/virtualaccount/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    reference = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

    payload = {
        "transaction": {"reference": reference},
        "order": {
            "amount": amount,
            "currency": settings.PSB_CURRENCY,
            "description": "Test Virtual Account Creation",
            "country": settings.PSB_COUNTRY,
            "amounttype": amount_type
        },
        "customer": {
            "account": {
                "name": name,
                "type": account_type
            }
        }
    }

    # --- Send the request ---
    response = requests.post(url, json=payload, headers=headers)

    # --- Debugging output ---
    print("🔹 CREATE URL:", url)
    print("🔹 HEADERS:", headers)
    print("🔹 PAYLOAD:", payload)
    print("🔹 STATUS:", response.status_code)
    print("🔹 TEXT:", response.text[:500])

    # --- Parse safely ---
    try:
        return response.json()
    except ValueError:
        raise Exception(f"Invalid JSON response from 9PSB: {response.text[:200]}")

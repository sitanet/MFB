# api/services/psb_service.py

import requests

class PSBService:
    BASE_URL = "https://api.9psb.com/wallet"  # replace with real 9PSB endpoint
    API_KEY = "your-9psb-api-key"

    @classmethod
    def create_wallet(cls, customer_data):
        url = f"{cls.BASE_URL}/create"
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "first_name": customer_data.first_name,
            "last_name": customer_data.last_name,
            "phone_number": customer_data.phone_no,
            "email": customer_data.email,
            "bvn": customer_data.bvn,
            "dob": str(customer_data.dob) if customer_data.dob else None,
            "gender": customer_data.cust_sex,
            "address": customer_data.address,
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.json()

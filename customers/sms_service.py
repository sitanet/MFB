import requests
from datetime import date
from .models import Customer

# Replace these with your actual credentials from Termii
TERMII_API_KEY = 'TLiLmGpgQLKmOMfqDEiGrcBBxDYRtoPwdQBjfUZDYaZxTOonoFxVksQGbfKkYP'  # Your Termii API Key
SENDER_ID = 'BSHL'  # Your Termii Sender ID (can be alphanumeric or your phone number)
BASE_URL = 'https://api.ng.termii.com/api/sms/send'  # Termii API endpoint for sending SMS

# SMS sending function using Termii
def send_sms(to_phone_number, message, bypass_dnd=False):
    url = BASE_URL
    headers = {
        'Content-Type': 'application/json',
    }

    # Set the channel based on whether DND bypass is needed
    channel = 'dnd' if bypass_dnd else 'generic'
    
    payload = {
        'api_key': TERMII_API_KEY,
        'from': SENDER_ID,
        'to': to_phone_number,
        'sms': message,
        'type': 'plain',  # You can also use 'flash' for flash SMS
        'channel': channel,  # Use 'dnd' to bypass DND
    }

    try:
        # Send SMS using POST request
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()  # Convert the response to JSON

        # Print the response for debugging
        print(f"Response from Termii: {response_data}")

        # Check for success in response
        if response.status_code == 200 and response_data.get('message') == 'Successfully Sent':
            return response_data
        else:
            # Return error message if something goes wrong
            return {
                "error": f"Failed to send SMS. Status code: {response.status_code}",
                "response": response_data
            }
    except requests.RequestException as e:
        # Catch any request errors and return them
        return {"error": str(e)}

# Example usage:
# send_sms('234XXXXXXXXXX', 'Hello from Termii!', bypass_dnd=True)





def send_birthday_wishes():
    today = date.today()
    customers_with_birthday_today = Customer.objects.filter(dob__month=today.month, dob__day=today.day)

    if not customers_with_birthday_today:
        return "No customers have birthdays today."

    for customer in customers_with_birthday_today:
        message = f"Happy Birthday {customer.get_full_name()}! Best wishes from our company!"
        send_sms(customer.phone_no, message)

    return f"Birthday wishes sent to {customers_with_birthday_today.count()} customers!"
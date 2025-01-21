import random

from customers.models import Customer


def generate_unique_6_digit_number():
    while True:
        # Generate a random 6-digit number
        ac_no = str(random.randint(10000, 99999))

        # Check if the generated number already exists in the Customer model
        if not Customer.objects.filter(ac_no=ac_no).exists():
            return ac_no
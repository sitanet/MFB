import random

from customers.models import Customer


def generate_unique_6_digit_number():
    while True:
        # Generate a random 6-digit number
        ac_no = str(random.randint(10000, 99999))

        # Check if the generated number already exists in the Customer model
        if not Customer.objects.filter(ac_no=ac_no).exists():
            return ac_no


def check_branch_customer_limit(branch_id):
    """
    Check if branch has reached its customer limit.
    
    Args:
        branch_id: The branch ID to check
        
    Returns:
        dict: {
            'can_add': bool - True if can add more customers,
            'current_count': int - Current customer count,
            'max_customers': int - Maximum allowed (0 = unlimited),
            'remaining': int or None - Remaining slots (None if unlimited),
            'message': str - User-friendly message
        }
    """
    from company.models import Branch
    
    try:
        branch = Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        return {
            'can_add': False,
            'current_count': 0,
            'max_customers': 0,
            'remaining': 0,
            'message': 'Branch not found.'
        }
    
    current_count = Customer.objects.filter(branch_id=branch_id).count()
    max_customers = branch.max_customers
    
    # 0 means unlimited
    if max_customers == 0:
        return {
            'can_add': True,
            'current_count': current_count,
            'max_customers': 0,
            'remaining': None,
            'message': 'Unlimited customers allowed.'
        }
    
    remaining = max_customers - current_count
    can_add = remaining > 0
    
    if can_add:
        message = f'{remaining} customer slot(s) remaining out of {max_customers}.'
    else:
        message = f'Customer limit reached. Maximum {max_customers} customers allowed for this branch.'
    
    return {
        'can_add': can_add,
        'current_count': current_count,
        'max_customers': max_customers,
        'remaining': remaining,
        'message': message
    }
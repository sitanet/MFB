from django.utils import timezone
from .models import Branch

def soon_to_expire(request):
    soon_expire_message = None
    if request.user.is_authenticated:
        try:
            # Access the branch_code directly from the related Branch model
            branch_code = request.user.branch.branch_code  # Assuming user has a related Branch object
            print(f"User's branch code: {branch_code}")

            # Find the corresponding branch
            branch = Branch.objects.get(branch_code=branch_code)
            print(f"Branch found: {branch}")

            # Access the expiration date from the associated company's model
            expiration_date = branch.company.expiration_date
            print(f"Expiration date: {expiration_date}")

            today = timezone.now().date()
            # Check if expiration date is within 30 days from today
            if expiration_date <= today + timezone.timedelta(days=30) and expiration_date >= today:
                soon_expire_message = "Your company's license will expire soon. Please contact your vendor."

        except Branch.DoesNotExist:
            soon_expire_message = "Company details not found. Please contact your vendor."
        except Exception as e:
            soon_expire_message = f"An error occurred: {str(e)}"
            print(f"Error: {str(e)}")
    
    return {'soon_expire_message': soon_expire_message}

# ninepsb/views.py
from django.http import JsonResponse
from .utils import create_virtual_account

def test_virtual_account(request):
    try:
        result = create_virtual_account(
            name="Test Customer",
            amount=100.00,
            account_type="STATIC",  # or "DYNAMIC"
            amount_type="EXACT"
        )
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


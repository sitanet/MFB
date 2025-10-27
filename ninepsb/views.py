from django.shortcuts import render

# Create your views here.
# ninepsb/views.py
from django.shortcuts import render
from django.contrib import messages
from .forms import BankFetchForm
from .services import fetch_and_update_psb_banks


def test_bank_fetch_view(request):
    """
    Simple form view to manually test 9PSB 'getbanks' endpoint.
    """
    result = None

    if request.method == "POST":
        form = BankFetchForm(request.POST)
        if form.is_valid():
            try:
                result = fetch_and_update_psb_banks()
                messages.success(request, result)
            except Exception as e:
                messages.error(request, f"❌ Error: {e}")
    else:
        form = BankFetchForm()

    return render(request, "ninepsb/test_bank_fetch.html", {
        "form": form,
        "result": result,
    })






from .forms import AccountValidationForm
from .services import psb_validate_account


from django.shortcuts import render
from django.contrib import messages
from .forms import AccountValidationForm
from .services import psb_validate_account





def test_account_validation_view(request):
    result = None
    account_name = None  # 👈 Add this

    if request.method == "POST":
        form = AccountValidationForm(request.POST)
        if form.is_valid():
            bank_code = form.cleaned_data["bank_code"]
            account_number = form.cleaned_data["account_number"]

            try:
                result = psb_validate_account(account_number, bank_code)

                # Extract name safely depending on 9PSB response structure
                if "customer" in result and "account" in result["customer"]:
                    account_name = result["customer"]["account"].get("name")
                elif "account_name" in result:
                    account_name = result["account_name"]

                if account_name:
                    messages.success(request, f"✅ Account validation successful! Account Name: {account_name}")
                else:
                    messages.success(request, "✅ Account validation successful (no name returned).")

            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Invalid input. Please try again.")
    else:
        form = AccountValidationForm()

    return render(
        request,
        "ninepsb/test_account_validation.html",
        {"form": form, "result": result, "account_name": account_name},
    )






from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from .services import psb_create_virtual_account_for_customer
from customers.models import Customer


def test_virtual_account_create(request, customer_id):
    """
    Web test page to create a 9PSB Virtual Account for an existing customer.
    Allows you to verify integration before full API deployment.
    """
    customer = get_object_or_404(Customer, id=customer_id)
    result = None

    if request.method == "POST":
        try:
            result = psb_create_virtual_account_for_customer(customer.id)

            # ✅ If successful, show confirmation and the details
            account_number = result.get("account_number") or "N/A"
            account_name = result.get("account_name") or "N/A"
            bank_name = result.get("bank_name") or "N/A"

            messages.success(
                request,
                f"✅ Virtual Account Created Successfully!<br>"
                f"<strong>Account Name:</strong> {account_name}<br>"
                f"<strong>Account Number:</strong> {account_number}<br>"
                f"<strong>Bank:</strong> {bank_name}",
            )

        except Exception as e:
            messages.error(request, f"❌ Failed: {str(e)}")

    return render(
        request,
        "ninepsb/test_virtual_account_customer.html",
        {"customer": customer, "result": result},
    )





from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
from datetime import datetime
from django.http import JsonResponse
from .forms import FundTransferForm
from .services import PSBService


# ==========================================================
# 1️⃣ Fund Transfer View
# ==========================================================
# ninepsb/views.py
# ninepsb/views.py
from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from datetime import datetime
from .forms import FundTransferForm
from .services import PSBService


def fund_transfer_view(request):
    form = FundTransferForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        psb = PSBService(settings.PSB_PUBLIC_KEY, settings.PSB_PRIVATE_KEY)

        tx_ref = f"FT{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            response = psb.fund_transfer(
                reference=tx_ref,
                amount=form.cleaned_data["amount"],
                description=form.cleaned_data.get("description", "Fund Transfer"),
                sender_account=form.cleaned_data["sender_account"],
                sender_name=form.cleaned_data["sender_name"],
                recipient_account=form.cleaned_data["recipient_account"],
                recipient_name=form.cleaned_data["recipient_name"],
                recipient_bank=form.cleaned_data["bank_code"],
            )
            messages.success(
                request,
                f"✅ Transfer successful! Ref: {response['transaction']['reference']}"
            )
        except Exception as e:
            messages.error(request, f"❌ Transfer failed: {str(e)}")

    return render(request, "ninepsb/fund_transfer.html", {"form": form})


# views.py
def account_enquiry_view(request):
    account_number = request.GET.get("account_number")
    bank_code = request.GET.get("bank_code")

    if not account_number or not bank_code:
        return JsonResponse({"success": False, "error": "Missing account or bank code"})

    try:
        psb = PSBService()
        result = psb.account_enquiry(account_number, bank_code)
        return JsonResponse({"success": True, "account_name": result["account_name"]})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
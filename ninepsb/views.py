# ninepsb/views.py
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .utils import create_virtual_account
from .services import WAASService


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


@login_required(login_url='login')
@staff_member_required
def wallet_enquiry_view(request):
    """
    9PSB Wallet Enquiry - Fetch wallet details by account number.
    """
    wallet_data = None
    account_no = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        elif len(account_no) != 10:
            error_message = "Wallet account number must be 10 digits"
        else:
            try:
                waas = WAASService()
                result = waas.wallet_enquiry(account_no)
                wallet_data = result.get('data', result)
                messages.success(request, "Wallet enquiry successful")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Wallet enquiry failed: {error_message}")
    
    context = {
        'wallet_data': wallet_data,
        'account_no': account_no,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/wallet_enquiry.html', context)


@login_required(login_url='login')
@staff_member_required
def wallet_status_view(request):
    """
    9PSB Wallet Status - Fetch wallet status by account number.
    """
    status_data = None
    account_no = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        else:
            try:
                waas = WAASService()
                result = waas.wallet_status(account_no)
                status_data = result.get('data', result)
                messages.success(request, "Wallet status fetched successfully")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Failed to fetch wallet status: {error_message}")
    
    context = {
        'status_data': status_data,
        'account_no': account_no,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/wallet_status.html', context)


@login_required(login_url='login')
@staff_member_required
def change_wallet_status_view(request):
    """
    9PSB Change Wallet Status - Activate or Suspend a wallet.
    """
    result_data = None
    account_no = None
    new_status = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        new_status = request.POST.get('new_status', '').strip().upper()
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        elif new_status not in ['ACTIVE', 'SUSPENDED']:
            error_message = "Status must be ACTIVE or SUSPENDED"
        else:
            try:
                waas = WAASService()
                result = waas.change_wallet_status(account_no, new_status)
                result_data = result.get('data', result)
                messages.success(request, f"Wallet status changed to {new_status}")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Failed to change wallet status: {error_message}")
    
    context = {
        'result_data': result_data,
        'account_no': account_no,
        'new_status': new_status,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/change_wallet_status.html', context)


@login_required(login_url='login')
@staff_member_required  
def wallet_transactions_view(request):
    """
    9PSB Wallet Transaction History - Fetch transaction history for a wallet.
    """
    transactions = None
    account_no = None
    from_date = None
    to_date = None
    error_message = None
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        from_date = request.POST.get('from_date', '')
        to_date = request.POST.get('to_date', '')
        num_items = request.POST.get('num_items', '50')
        
        if not account_no:
            error_message = "Please enter a wallet account number"
        elif not from_date or not to_date:
            error_message = "Please enter both from and to dates"
        else:
            try:
                waas = WAASService()
                result = waas.wallet_transactions(account_no, from_date, to_date, int(num_items))
                transactions = result.get('data', result)
                messages.success(request, "Transaction history fetched successfully")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Failed to fetch transaction history: {error_message}")
    
    context = {
        'transactions': transactions,
        'account_no': account_no,
        'from_date': from_date,
        'to_date': to_date,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/wallet_transactions.html', context)


@login_required(login_url='login')
@staff_member_required
def get_banks_view(request):
    """
    9PSB Get Banks - Fetch list of all banks.
    """
    banks = None
    error_message = None
    
    try:
        waas = WAASService()
        result = waas.get_banks()
        banks = result.get('data', result)
    except Exception as e:
        error_message = str(e)
        messages.error(request, f"Failed to fetch banks: {error_message}")
    
    context = {
        'banks': banks,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/get_banks.html', context)


@login_required(login_url='login')
@staff_member_required
def other_bank_enquiry_view(request):
    """
    9PSB Other Bank Enquiry - Verify account details of other bank's account.
    """
    account_data = None
    account_no = None
    bank_code = None
    error_message = None
    banks = None
    
    # Always fetch banks for the dropdown
    try:
        waas = WAASService()
        result = waas.get_banks()
        banks = result.get('data', [])
    except Exception as e:
        messages.warning(request, f"Could not load banks list: {str(e)}")
    
    if request.method == 'POST':
        account_no = request.POST.get('account_no', '').strip()
        bank_code = request.POST.get('bank_code', '').strip()
        
        if not account_no:
            error_message = "Please enter an account number"
        elif not bank_code:
            error_message = "Please select a bank"
        else:
            try:
                waas = WAASService()
                result = waas.other_bank_enquiry(account_no, bank_code)
                account_data = result.get('data', result)
                messages.success(request, "Account enquiry successful")
            except Exception as e:
                error_message = str(e)
                messages.error(request, f"Account enquiry failed: {error_message}")
    
    context = {
        'account_data': account_data,
        'account_no': account_no,
        'bank_code': bank_code,
        'banks': banks,
        'error_message': error_message,
    }
    return render(request, 'ninepsb/other_bank_enquiry.html', context)


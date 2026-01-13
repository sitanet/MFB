from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Max  # Add Max import
from functools import wraps

from .models import FixedDeposit
from customers.models import FixedDepositAccount, Customer
from transactions.models import Memtrans
from .forms import FixedDepositForm

from customers.models import Customer


def require_fixed_deposit_feature(view_func):
    """Decorator to check if branch has Fixed Deposit feature enabled"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if hasattr(request.user, 'branch') and request.user.branch:
            if not request.user.branch.can_fixed_deposit:
                messages.error(request, "Fixed Deposit feature is not enabled for your branch. Please contact administrator.")
                return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_fixed_deposit_feature
def display_customers_with_fixed_deposit(request):
    """
    Show only customers who have Fixed Deposit accounts (gl_name = 'FIXED DEPOSIT').
    """
    from accounts.utils import get_company_branch_ids
    from accounts_admin.models import Account
    
    branch_ids = get_company_branch_ids(request.user)
    
    # Get GL numbers for accounts named "FIXED DEPOSIT"
    fd_gl_numbers = Account.all_objects.filter(
        gl_name__icontains='fixed deposit'
    ).values_list('gl_no', flat=True)
    
    # Show only customers with Fixed Deposit GL numbers
    customers = Customer.all_objects.filter(
        branch_id__in=branch_ids,
        gl_no__in=fd_gl_numbers
    ).select_related("branch")
    
    fixed_accounts = FixedDepositAccount.objects.filter(
        branch_id__in=branch_ids
    ).select_related("customer")

    return render(request, "fixed_deposit/customers_list.html", {
        "customers": customers,
        "fixed_accounts": fixed_accounts
    })



@require_fixed_deposit_feature
def display_customers_for_fixed_deposit_withdrawal(request):
    # Get customers who have an active Fixed Deposit
    fixed_deposits = FixedDeposit.objects.select_related("customer")

    return render(request, "fixed_deposit/customers_with_fixed_deposit.html", {
        "fixed_deposits": fixed_deposits  # Ensure it matches the template variable
    })



from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction, models
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from .forms import FixedDepositForm, FixedDepositWithdrawalForm
from .models import FixedDepositHist  # Import FixedDepositHist model
from customers.models import Customer
from company.models import Branch
from transactions.models import Memtrans
from transactions.utils import generate_fixed_deposit_id
from accounts_admin.models import Account


import logging

logger = logging.getLogger(__name__)

# 🔹 Function to get customer account balance
def get_account_balance(gl_no, ac_no):
    """Returns the account balance by summing all transactions."""
    debit_total = Memtrans.objects.filter(gl_no=gl_no, ac_no=ac_no, amount__lt=0).aggregate(
        total_debit=models.Sum("amount")
    )["total_debit"] or 0  # Sum of all debits (negative)

    credit_total = Memtrans.objects.filter(gl_no=gl_no, ac_no=ac_no, amount__gt=0).aggregate(
        total_credit=models.Sum("amount")
    )["total_credit"] or 0  # Sum of all credits (positive)

    return credit_total + debit_total  # Net balance




@require_fixed_deposit_feature
def register_fixed_deposit(request):
    customer_id = request.GET.get("customer_id")
    customer = None
    form = FixedDepositForm()
    fixed_int_gl_no = None
    fixed_int_ac_no = None

    if customer_id:
        customer = get_object_or_404(Customer, id=customer_id)
        form = FixedDepositForm(initial={
            "customer": customer.id,
            "fixed_gl_no": customer.gl_no,
            "fixed_ac_no": customer.ac_no,
        })

    if request.method == "POST":
        form = FixedDepositForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    fixed_deposit = form.save(commit=False)

                    # Ensure branch is set
                    if customer and hasattr(customer, "branch") and customer.branch:
                        fixed_deposit.branch = customer.branch
                    else:
                        fixed_deposit.branch = Branch.objects.first()
                        if not fixed_deposit.branch:
                            messages.error(request, "⚠️ No branch found.")
                            return render(request, "fixed_deposit/fixed_deposit_form.html", {"form": form, "customer": customer})

                    # Fetch Fixed Interest GL and AC from Account model
                    account = Account.objects.filter(gl_no=fixed_deposit.fixed_gl_no).first()
                    if account:
                        fixed_int_gl_no = account.fixed_dep_int_gl_no
                        fixed_int_ac_no = account.fixed_dep_int_ac_no
                    else:
                        messages.error(request, "⚠️ No matching account found for the selected Fixed GL No.")
                        return render(request, "fixed_deposit/fixed_deposit_form.html", {"form": form, "customer": customer})

                    # Validate sufficient balance
                    cust_balance = get_account_balance(fixed_deposit.cust_gl_no, fixed_deposit.cust_ac_no)
                    if cust_balance < fixed_deposit.deposit_amount:
                        messages.error(request, "❌ Insufficient funds in the account.")
                        return render(request, "fixed_deposit/fixed_deposit_form.html", {"form": form, "customer": customer})

                    # Calculate the cycle number
                    last_cycle = FixedDeposit.objects.filter(
                        fixed_gl_no=fixed_deposit.fixed_gl_no,
                        fixed_ac_no=fixed_deposit.fixed_ac_no
                    ).aggregate(Max("cycle"))["cycle__max"] or 0
                    fixed_deposit.cycle = last_cycle + 1

                    # Save Fixed Deposit
                    fixed_deposit.fixed_int_gl_no = fixed_int_gl_no or "DEFAULT_GL_NO"
                    fixed_deposit.fixed_int_ac_no = fixed_int_ac_no or "DEFAULT_AC_NO"
                    fixed_deposit.save()

                    # Generate unique transaction number
                    trx_no = generate_fixed_deposit_id()

                    # Record Transaction Entries
                    user = request.user
                    transactions = [
                        Memtrans(
                            branch=fixed_deposit.branch,
                            customer=fixed_deposit.customer,
                            gl_no=fixed_deposit.cust_gl_no,
                            ac_no=fixed_deposit.cust_ac_no,
                            trx_no=trx_no,
                            ses_date=fixed_deposit.start_date,
                            sys_date=now(),
                            amount=-fixed_deposit.deposit_amount,
                            description=f"Fixed Deposit Debit (Cycle {fixed_deposit.cycle})",
                            type="C",
                            account_type="C",
                            code="FD",
                            user=user,
                            cust_branch=user.branch,
                            cycle=fixed_deposit.cycle,
                        ),
                        Memtrans(
                            branch=fixed_deposit.branch,
                            customer=fixed_deposit.customer,
                            gl_no=fixed_deposit.fixed_gl_no,
                            ac_no=fixed_deposit.fixed_ac_no,
                            trx_no=trx_no,
                            ses_date=fixed_deposit.start_date,
                            sys_date=now(),
                            amount=fixed_deposit.deposit_amount,
                            description=f"Fixed Deposit Credit (Cycle {fixed_deposit.cycle})",
                            type="C",
                            account_type="C",
                            code="FD",
                            user=user,
                            cust_branch=user.branch,
                            cycle=fixed_deposit.cycle,
                        )
                    ]
                    Memtrans.objects.bulk_create(transactions)

                    # Log in Fixed Deposit History
                    FixedDepositHist.objects.create(
                        branch=fixed_deposit.branch,
                        fixed_gl_no=fixed_deposit.fixed_gl_no,
                        fixed_ac_no=fixed_deposit.fixed_ac_no,
                        trx_date=fixed_deposit.start_date,
                        trx_type="FD",
                        trx_naration=f"Fixed deposit initiated (Cycle {fixed_deposit.cycle})",
                        trx_no=trx_no,
                        principal=fixed_deposit.deposit_amount,
                        interest=fixed_deposit.interest_amount or 0.00,
                    )

                    messages.success(request, "✅ Fixed Deposit registered successfully!")
                    return redirect("display_customers_with_fixed_deposit")

            except Exception as e:
                logger.error(f"⚠️ Error processing fixed deposit: {e}", exc_info=True)
                messages.error(request, "⚠️ An unexpected error occurred. Please try again.")

    # Filter customers by company
    from accounts.utils import get_branch_from_vendor_db
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    if user_branch:
        customers_qs = Customer.all_objects.filter(branch__company=user_branch.company)
    else:
        customers_qs = Customer.objects.none()
    
    return render(request, "fixed_deposit/fixed_deposit_form.html", {
        "form": form,
        "customer": customer,
        "customers": customers_qs,
        "fixed_int_gl_no": fixed_int_gl_no,
        "fixed_int_ac_no": fixed_int_ac_no,
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils.timezone import now
import logging
from .models import FixedDeposit, FixedDepositHist
from .forms import FixedDepositWithdrawalForm
from transactions.utils import generate_fixed_deposit_id
from transactions.models import Memtrans
from accounts_admin.models import Account

logger = logging.getLogger(__name__)


@require_fixed_deposit_feature
def withdraw_fixed_deposit(request, uuid):
    fixed_deposit = get_object_or_404(FixedDeposit, uuid=uuid)

    # Prefill the form with existing data
    initial_data = {
        "customer": fixed_deposit.customer.id,
        "cust_gl_no": fixed_deposit.cust_gl_no,
        "cust_ac_no": fixed_deposit.cust_ac_no,
        "fixed_gl_no": fixed_deposit.fixed_gl_no,
        "fixed_ac_no": fixed_deposit.fixed_ac_no,
        "deposit_amount": fixed_deposit.deposit_amount,
        "interest_amount": fixed_deposit.interest_amount or 0.00,
        "withdraw_amount": fixed_deposit.deposit_amount,  # Default to full amount
    }

    form = FixedDepositWithdrawalForm(initial=initial_data)

    if request.method == "POST":
        form = FixedDepositWithdrawalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    withdraw_amount = form.cleaned_data["withdraw_amount"]
                    interest_amount = form.cleaned_data["interest_amount"]
                    user = request.user
                    branch = fixed_deposit.branch

                    # Validate sufficient balance
                    fixed_account_balance = get_account_balance(
                        fixed_deposit.fixed_gl_no, fixed_deposit.fixed_ac_no
                    )
                    total_withdraw = withdraw_amount

                    if fixed_account_balance < total_withdraw:
                        messages.error(request, "❌ Insufficient funds in the Fixed Deposit account.")
                        return render(request, "fixed_deposit/fixed_deposit_withdrawal.html", {"form": form})

                    # Get Fixed Interest GL & AC
                    account = Account.objects.filter(gl_no=fixed_deposit.fixed_gl_no).first()
                    fixed_int_gl_no = account.fixed_dep_int_gl_no if account else None
                    fixed_int_ac_no = account.fixed_dep_int_ac_no if account else None

                    if not (fixed_int_gl_no and fixed_int_ac_no):
                        messages.error(request, "⚠️ No Fixed Interest Account found for this deposit.")
                        return render(request, "fixed_deposit/fixed_deposit_withdrawal.html", {"form": form})

                    # Generate unique transaction number
                    trx_no = generate_fixed_deposit_id()

                    # Create transaction records with the same cycle as the fixed deposit
                    transactions = [
                        # Debit Fixed Deposit Account
                        Memtrans(
                            branch=branch, customer=fixed_deposit.customer, gl_no=fixed_deposit.fixed_gl_no,
                            ac_no=fixed_deposit.fixed_ac_no, trx_no=trx_no, ses_date=now(), sys_date=now(),
                            amount=-withdraw_amount, description="Fixed Deposit Withdrawal", type="D",
                            account_type="C", code="FDW", user=user, cust_branch=user.branch,
                            cycle=fixed_deposit.cycle  # Include the same cycle
                        ),
                        # Credit Customer Account
                        Memtrans(
                            branch=branch, customer=fixed_deposit.customer, gl_no=fixed_deposit.cust_gl_no,
                            ac_no=fixed_deposit.cust_ac_no, trx_no=trx_no, ses_date=now(), sys_date=now(),
                            amount=withdraw_amount, description="Fixed Deposit Withdrawal Credit", type="C",
                            account_type="C", code="FDW", user=user, cust_branch=user.branch,
                            cycle=fixed_deposit.cycle  # Include the same cycle
                        ),
                    ]

                    # Handle interest transactions if applicable
                    if interest_amount > 0:
                        transactions.extend([
                            # Debit Fixed Interest Account
                            Memtrans(
                                branch=branch, customer=fixed_deposit.customer, gl_no=fixed_int_gl_no,
                                ac_no=fixed_int_ac_no, trx_no=trx_no, ses_date=now(), sys_date=now(),
                                amount=-interest_amount, description="Fixed Deposit Interest Debit", type="D",
                                account_type="C", code="FDI", user=user, cust_branch=user.branch,
                                cycle=fixed_deposit.cycle  # Include the same cycle
                            ),
                            # Credit Interest to Customer
                            Memtrans(
                                branch=branch, customer=fixed_deposit.customer, gl_no=fixed_deposit.cust_gl_no,
                                ac_no=fixed_deposit.cust_ac_no, trx_no=trx_no, ses_date=now(), sys_date=now(),
                                amount=interest_amount, description="Fixed Deposit Interest Credit", type="C",
                                account_type="C", code="FDI", user=user, cust_branch=user.branch,
                                cycle=fixed_deposit.cycle  # Include the same cycle
                            )
                        ])

                    # Bulk insert transactions
                    Memtrans.objects.bulk_create(transactions)

                    # Log withdrawal history with the same cycle
                    FixedDepositHist.objects.create(
                        branch=branch, fixed_gl_no=fixed_deposit.fixed_gl_no, fixed_ac_no=fixed_deposit.fixed_ac_no,
                        trx_date=now(), trx_type="FDW", trx_naration="Fixed deposit withdrawn",
                        trx_no=trx_no, principal=-withdraw_amount, interest=-interest_amount,
                        # cycle=fixed_deposit.cycle  # Include the same cycle
                    )

                    # Update FixedDeposit status to "closed" instead of deleting
                    fixed_deposit.status = "closed"
                    fixed_deposit.save()

                    messages.success(request, "✅ Fixed Deposit withdrawn successfully!")
                    logger.info(f"Fixed Deposit {fixed_deposit.fixed_ac_no} withdrawn successfully by user {request.user}.")
                    return redirect("display_customers_for_fixed_deposit_withdrawal")

            except Exception as e:
                logger.error(f"⚠️ Error processing withdrawal: {e}", exc_info=True)
                messages.error(request, "⚠️ An unexpected error occurred. Please try again.")
        else:
            messages.error(request, "❌ Form submission failed. Please check the fields.")
            return render(request, "fixed_deposit/fixed_deposit_withdrawal.html", {"form": form, "customer": fixed_deposit.customer})

    return render(request, "fixed_deposit/fixed_deposit_withdrawal.html", {
        "form": form,
        "customer": fixed_deposit.customer,
    })

from django.utils.timezone import now
from .models import FixedDeposit  # Import FixedDeposit model


@require_fixed_deposit_feature
def running_fixed_deposits(request):
    """Fetch and display all currently active fixed deposits."""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    running_deposits = FixedDeposit.objects.filter(start_date__lte=now(), maturity_date__gte=now(), branch_id__in=branch_ids)

    return render(request, "fixed_deposit/running_fixed_deposits.html", {
        "running_deposits": running_deposits
    })







from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.utils.timezone import now
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


@require_fixed_deposit_feature
def reversal_for_fixed_deposit(request, uuid):
    fixed_deposit = get_object_or_404(FixedDeposit, uuid=uuid)

    # 🚨 Prevent reversal if status is "closed"
    if fixed_deposit.status.lower() == "closed":
        messages.error(request, "❌ This Fixed Deposit has already been closed and cannot be reversed.")
        return redirect("display_customers_with_fixed_deposit")

    if request.method == "POST":
        try:
            with transaction.atomic():
                user = request.user  # Get logged-in user

                # Find the original transactions for both customer and fixed deposit account with the same cycle
                original_transactions = Memtrans.objects.filter(
                    gl_no__in=[fixed_deposit.cust_gl_no, fixed_deposit.fixed_gl_no],
                    ac_no__in=[fixed_deposit.cust_ac_no, fixed_deposit.fixed_ac_no],
                    cycle=fixed_deposit.cycle  # Filter by the same cycle
                )

                if not original_transactions.exists():
                    messages.error(request, "❌ Original transactions not found for reversal.")
                    return redirect("display_customers_with_fixed_deposit")

                # Debugging: Log original transactions
                logger.debug(f"Original Transactions: {original_transactions}")

                # Update the existing transactions to mark them as errors (error="H")
                for original_transaction in original_transactions:
                    original_transaction.error = "H"  # Set error to "H"
                    original_transaction.description = f"Reversal: {original_transaction.description}"
                    original_transaction.save()  # Save the updated transaction

                # Log in Fixed Deposit History (optional, if needed)
                FixedDepositHist.objects.create(
                    branch=fixed_deposit.branch,
                    fixed_gl_no=fixed_deposit.fixed_gl_no,
                    fixed_ac_no=fixed_deposit.fixed_ac_no,
                    trx_date=now(),
                    trx_type="FD-REV",
                    trx_naration="Fixed Deposit Reversed",
                    trx_no=generate_fixed_deposit_id(),  # Generate a new transaction number for history
                    principal=-fixed_deposit.deposit_amount,
                    interest=-(fixed_deposit.interest_amount or 0.00),
                    # cycle=fixed_deposit.cycle  # Include the same cycle
                )

                # Delete the fixed deposit record (optional, if needed)
                fixed_deposit.delete()

                messages.success(request, "✅ Fixed Deposit successfully reversed!")
                return redirect("display_customers_with_fixed_deposit")

        except Exception as e:
            logger.error(f"⚠️ Error processing fixed deposit reversal: {e}", exc_info=True)
            messages.error(request, "⚠️ An unexpected error occurred. Please try again.")

    return render(request, "fixed_deposit/fixed_deposit_reversal.html", {
        "fixed_deposit": fixed_deposit
    })






from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.utils.timezone import now
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


@require_fixed_deposit_feature
def reverse_fixed_deposit_withdrawal(request, uuid):
    withdrawal = get_object_or_404(FixedDepositWithdrawal, uuid=uuid)

    # Prevent reversal if status is "closed"
    if withdrawal.status.lower() == "closed":
        messages.error(request, "❌ This Fixed Deposit Withdrawal has already been closed and cannot be reversed.")
        return redirect("display_customers_with_fixed_deposit")

    if request.method == "POST":
        try:
            with transaction.atomic():
                user = request.user  # Get logged-in user

                # Retrieve original transactions linked to this withdrawal
                original_transactions = Memtrans.objects.filter(
                    gl_no__in=[withdrawal.cust_gl_no, withdrawal.fixed_gl_no],
                    ac_no__in=[withdrawal.cust_ac_no, withdrawal.fixed_ac_no],
                    cycle=withdrawal.cycle
                )

                if not original_transactions.exists():
                    messages.error(request, "❌ Original transactions not found for reversal.")
                    return redirect("display_customers_with_fixed_deposit")

                # Log original transactions for debugging
                logger.debug(f"Original Transactions: {original_transactions}")

                # Mark original transactions as reversed
                for transaction in original_transactions:
                    transaction.error = "H"
                    transaction.description = f"Reversal: {transaction.description}"
                    transaction.save()

                # Log in Fixed Deposit Withdrawal History
                FixedDepositHist.objects.create(
                    branch=withdrawal.branch,
                    fixed_gl_no=withdrawal.fixed_gl_no,
                    fixed_ac_no=withdrawal.fixed_ac_no,
                    trx_date=now(),
                    trx_type="FD-WD-REV",
                    trx_naration="Fixed Deposit Withdrawal Reversed",
                    trx_no=generate_fixed_deposit_id(),
                    principal=withdrawal.withdrawal_amount,
                    interest=(withdrawal.interest_amount or 0.00),
                )

                # Remove the withdrawal record
                withdrawal.delete()

                messages.success(request, "✅ Fixed Deposit Withdrawal successfully reversed!")
                return redirect("display_customers_with_fixed_deposit")

        except Exception as e:
            logger.error(f"⚠️ Error processing fixed deposit withdrawal reversal: {e}", exc_info=True)
            messages.error(request, "⚠️ An unexpected error occurred. Please try again.")

    return render(request, "fixed_deposit/fixed_deposit_withdrawal_reversal.html", {"withdrawal": withdrawal})





@require_fixed_deposit_feature
def reversal_fixed_deposit_list(request):
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    fixed_deposits = FixedDeposit.objects.filter(status="active", branch_id__in=branch_ids)
    print(f"Found {fixed_deposits.count()} active deposits")  # Debugging line
    return render(request, "fixed_deposit/reverse_fixed_deposit_list.html", {"fixed_deposits": fixed_deposits})





@require_fixed_deposit_feature
def list_fixed_deposit_withdrawals(request):
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    withdrawals = FixedDeposit.objects.filter(branch_id__in=branch_ids)
    return render(request, "fixed_deposit/fixed_deposit_withdrawal_list.html", {"withdrawals": withdrawals})


@require_fixed_deposit_feature
def fixed_dep(request):
    return render(request, 'fixed_deposit/fixed_dep.html')


# ==================== NEW VIEWS FOR STANDARD MFB FIXED DEPOSIT ====================

from datetime import date
from decimal import Decimal
from .models import FDProduct, FDInterestSlab, FDInterestAccrual, FDRenewalHistory
from .forms import FDRenewalForm, FDProductForm, LienMarkingForm


@require_fixed_deposit_feature
def renew_fixed_deposit(request, uuid):
    """Renew an existing fixed deposit at maturity"""
    fixed_deposit = get_object_or_404(FixedDeposit, uuid=uuid)
    
    # Check if FD can be renewed
    if fixed_deposit.status not in ['active', 'matured']:
        messages.error(request, "This Fixed Deposit cannot be renewed.")
        return redirect("running_fixed_deposits")
    
    if request.method == "POST":
        form = FDRenewalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    renewal_type = form.cleaned_data['renewal_type']
                    new_tenure = form.cleaned_data['new_tenure_months']
                    new_rate = form.cleaned_data['new_interest_rate']
                    new_interest_type = form.cleaned_data['new_interest_type']
                    
                    # Calculate renewed principal based on renewal type
                    if renewal_type == 'principal_only':
                        renewed_principal = fixed_deposit.deposit_amount
                    elif renewal_type == 'principal_interest':
                        renewed_principal = fixed_deposit.maturity_amount
                    else:  # custom
                        renewed_principal = form.cleaned_data['custom_amount']
                    
                    # Create renewal history record
                    FDRenewalHistory.objects.create(
                        original_fd=fixed_deposit,
                        branch=fixed_deposit.branch,
                        renewal_date=date.today(),
                        original_principal=fixed_deposit.deposit_amount,
                        interest_earned=fixed_deposit.interest_amount,
                        renewal_type=renewal_type,
                        renewed_principal=renewed_principal,
                        new_tenure_months=new_tenure,
                        new_interest_rate=new_rate,
                        is_auto_renewal=False,
                        remarks=form.cleaned_data.get('remarks', ''),
                        created_by=request.user.username
                    )
                    
                    # Update old FD status
                    fixed_deposit.status = 'renewed'
                    fixed_deposit.save()
                    
                    # Create new FD
                    new_fd = FixedDeposit.objects.create(
                        customer=fixed_deposit.customer,
                        cust_gl_no=fixed_deposit.cust_gl_no,
                        cust_ac_no=fixed_deposit.cust_ac_no,
                        fixed_gl_no=fixed_deposit.fixed_gl_no,
                        fixed_ac_no=fixed_deposit.fixed_ac_no,
                        branch=fixed_deposit.branch,
                        deposit_amount=renewed_principal,
                        interest_rate=new_rate,
                        tenure_months=new_tenure,
                        start_date=date.today(),
                        maturity_date=date.today() + timedelta(days=new_tenure * 30),
                        interest_type=new_interest_type,
                        auto_renewal=fixed_deposit.auto_renewal,
                        original_fd=fixed_deposit,
                        renewal_count=fixed_deposit.renewal_count + 1,
                        nominee_name=fixed_deposit.nominee_name,
                        nominee_relationship=fixed_deposit.nominee_relationship,
                        nominee_phone=fixed_deposit.nominee_phone,
                        nominee_address=fixed_deposit.nominee_address,
                        created_by=request.user.username,
                        cycle=fixed_deposit.cycle + 1 if fixed_deposit.cycle else 1,
                    )
                    
                    # Generate transaction entries for renewal
                    trx_no = generate_fixed_deposit_id()
                    FixedDepositHist.objects.create(
                        branch=fixed_deposit.branch,
                        fixed_gl_no=fixed_deposit.fixed_gl_no,
                        fixed_ac_no=fixed_deposit.fixed_ac_no,
                        trx_date=date.today(),
                        trx_type="FD-REN",
                        trx_naration=f"FD Renewed - {renewal_type}",
                        trx_no=trx_no,
                        principal=renewed_principal,
                        interest=fixed_deposit.interest_amount,
                    )
                    
                    messages.success(request, f"Fixed Deposit renewed successfully! New FD: {new_fd.fixed_ac_no}")
                    return redirect("running_fixed_deposits")
                    
            except Exception as e:
                logger.error(f"Error renewing FD: {e}", exc_info=True)
                messages.error(request, "An error occurred while renewing the Fixed Deposit.")
    else:
        form = FDRenewalForm(initial={
            'new_tenure_months': fixed_deposit.tenure_months,
            'new_interest_rate': fixed_deposit.interest_rate,
            'new_interest_type': fixed_deposit.interest_type,
        })
    
    return render(request, "fixed_deposit/renew_fixed_deposit.html", {
        "form": form,
        "fixed_deposit": fixed_deposit,
    })


@require_fixed_deposit_feature
def generate_fd_certificate(request, uuid):
    """Generate FD certificate for printing"""
    fixed_deposit = get_object_or_404(FixedDeposit, uuid=uuid)
    
    # Generate certificate number if not exists
    if not fixed_deposit.certificate_number:
        fixed_deposit.generate_certificate_number()
        fixed_deposit.certificate_issued = True
        fixed_deposit.certificate_issue_date = date.today()
        fixed_deposit.save()
    
    context = {
        "fd": fixed_deposit,
        "customer": fixed_deposit.customer,
        "branch": fixed_deposit.branch,
        "print_date": date.today(),
    }
    
    return render(request, "fixed_deposit/fd_certificate.html", context)


@require_fixed_deposit_feature
def premature_withdrawal(request, uuid):
    """Handle premature withdrawal with penalty calculation"""
    fixed_deposit = get_object_or_404(FixedDeposit, uuid=uuid)
    
    # Check if premature withdrawal is allowed
    can_withdraw, message = fixed_deposit.can_withdraw_premature()
    if not can_withdraw:
        messages.error(request, message)
        return redirect("running_fixed_deposits")
    
    # Calculate premature interest and penalty
    net_interest, penalty = fixed_deposit.calculate_premature_interest()
    
    initial_data = {
        "customer": fixed_deposit.customer.id,
        "cust_gl_no": fixed_deposit.cust_gl_no,
        "cust_ac_no": fixed_deposit.cust_ac_no,
        "fixed_gl_no": fixed_deposit.fixed_gl_no,
        "fixed_ac_no": fixed_deposit.fixed_ac_no,
        "deposit_amount": fixed_deposit.deposit_amount,
        "interest_amount": net_interest,
        "penalty_amount": penalty,
        "withdraw_amount": fixed_deposit.get_available_for_withdrawal(),
        "is_premature": True,
        "tds_amount": fixed_deposit.tds_deducted if fixed_deposit.tds_applicable else Decimal("0.00"),
    }
    
    # Calculate net payable
    net_payable = (fixed_deposit.get_available_for_withdrawal() + net_interest - 
                   penalty - initial_data["tds_amount"])
    initial_data["net_payable"] = net_payable
    
    from .forms import FixedDepositWithdrawalForm
    form = FixedDepositWithdrawalForm(initial=initial_data)
    
    if request.method == "POST":
        form = FixedDepositWithdrawalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    withdraw_amount = form.cleaned_data["withdraw_amount"]
                    interest_amount = form.cleaned_data["interest_amount"]
                    penalty_amount = form.cleaned_data.get("penalty_amount", Decimal("0.00"))
                    tds_amount = form.cleaned_data.get("tds_amount", Decimal("0.00"))
                    
                    user = request.user
                    branch = fixed_deposit.branch
                    trx_no = generate_fixed_deposit_id()
                    
                    # Create transaction records
                    transactions_list = [
                        # Debit Fixed Deposit Account
                        Memtrans(
                            branch=branch, customer=fixed_deposit.customer, 
                            gl_no=fixed_deposit.fixed_gl_no, ac_no=fixed_deposit.fixed_ac_no,
                            trx_no=trx_no, ses_date=now(), sys_date=now(),
                            amount=-withdraw_amount, 
                            description="Premature FD Withdrawal", type="D",
                            account_type="C", code="FDPW", user=user, 
                            cust_branch=user.branch, cycle=fixed_deposit.cycle
                        ),
                        # Credit Customer Account (Principal)
                        Memtrans(
                            branch=branch, customer=fixed_deposit.customer,
                            gl_no=fixed_deposit.cust_gl_no, ac_no=fixed_deposit.cust_ac_no,
                            trx_no=trx_no, ses_date=now(), sys_date=now(),
                            amount=withdraw_amount, 
                            description="Premature FD Withdrawal Credit", type="C",
                            account_type="C", code="FDPW", user=user,
                            cust_branch=user.branch, cycle=fixed_deposit.cycle
                        ),
                    ]
                    
                    # Handle interest (net of penalty and TDS)
                    net_interest_payable = interest_amount - penalty_amount - tds_amount
                    if net_interest_payable > 0:
                        account = Account.objects.filter(gl_no=fixed_deposit.fixed_gl_no).first()
                        fixed_int_gl_no = account.fixed_dep_int_gl_no if account else fixed_deposit.fixed_int_gl_no
                        fixed_int_ac_no = account.fixed_dep_int_ac_no if account else fixed_deposit.fixed_int_ac_no
                        
                        transactions_list.extend([
                            Memtrans(
                                branch=branch, customer=fixed_deposit.customer,
                                gl_no=fixed_int_gl_no, ac_no=fixed_int_ac_no,
                                trx_no=trx_no, ses_date=now(), sys_date=now(),
                                amount=-interest_amount,
                                description="FD Interest (Premature)", type="D",
                                account_type="C", code="FDI", user=user,
                                cust_branch=user.branch, cycle=fixed_deposit.cycle
                            ),
                            Memtrans(
                                branch=branch, customer=fixed_deposit.customer,
                                gl_no=fixed_deposit.cust_gl_no, ac_no=fixed_deposit.cust_ac_no,
                                trx_no=trx_no, ses_date=now(), sys_date=now(),
                                amount=net_interest_payable,
                                description="FD Interest Credit (Net)", type="C",
                                account_type="C", code="FDI", user=user,
                                cust_branch=user.branch, cycle=fixed_deposit.cycle
                            ),
                        ])
                    
                    Memtrans.objects.bulk_create(transactions_list)
                    
                    # Log history
                    FixedDepositHist.objects.create(
                        branch=branch,
                        fixed_gl_no=fixed_deposit.fixed_gl_no,
                        fixed_ac_no=fixed_deposit.fixed_ac_no,
                        trx_date=now(),
                        trx_type="FDPW",
                        trx_naration=f"Premature withdrawal - Penalty: {penalty_amount}",
                        trx_no=trx_no,
                        principal=-withdraw_amount,
                        interest=-interest_amount,
                    )
                    
                    # Update FD status and penalty
                    fixed_deposit.status = "premature_closed"
                    fixed_deposit.penalty_amount = penalty_amount
                    fixed_deposit.save()
                    
                    messages.success(request, f"Premature withdrawal successful! Penalty: {penalty_amount}")
                    return redirect("running_fixed_deposits")
                    
            except Exception as e:
                logger.error(f"Error in premature withdrawal: {e}", exc_info=True)
                messages.error(request, "An error occurred. Please try again.")
    
    return render(request, "fixed_deposit/premature_withdrawal.html", {
        "form": form,
        "fixed_deposit": fixed_deposit,
        "penalty": penalty,
        "net_interest": net_interest,
        "days_held": (date.today() - fixed_deposit.start_date).days,
    })


@require_fixed_deposit_feature
def mark_lien(request, uuid):
    """Mark or remove lien on Fixed Deposit"""
    fixed_deposit = get_object_or_404(FixedDeposit, uuid=uuid)
    
    if request.method == "POST":
        form = LienMarkingForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            
            if action == 'mark':
                lien_amount = form.cleaned_data['lien_amount']
                if lien_amount > fixed_deposit.deposit_amount:
                    messages.error(request, "Lien amount cannot exceed deposit amount.")
                else:
                    fixed_deposit.is_lien_marked = True
                    fixed_deposit.lien_amount = lien_amount
                    fixed_deposit.lien_reference = form.cleaned_data.get('loan_reference', '')
                    fixed_deposit.lien_date = date.today()
                    fixed_deposit.save()
                    messages.success(request, f"Lien of {lien_amount} marked successfully.")
            else:  # remove
                fixed_deposit.is_lien_marked = False
                fixed_deposit.lien_amount = Decimal("0.00")
                fixed_deposit.lien_reference = None
                fixed_deposit.lien_date = None
                fixed_deposit.save()
                messages.success(request, "Lien removed successfully.")
            
            return redirect("running_fixed_deposits")
    else:
        form = LienMarkingForm(initial={
            'lien_amount': fixed_deposit.lien_amount,
            'loan_reference': fixed_deposit.lien_reference,
        })
    
    return render(request, "fixed_deposit/mark_lien.html", {
        "form": form,
        "fixed_deposit": fixed_deposit,
    })


@require_fixed_deposit_feature
def fd_product_list(request):
    """List all FD Products"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    products = FDProduct.objects.filter(branch_id__in=branch_ids)
    return render(request, "fixed_deposit/fd_product_list.html", {"products": products})


@require_fixed_deposit_feature
def fd_product_create(request):
    """Create new FD Product"""
    if request.method == "POST":
        form = FDProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.branch = request.user.branch
            product.save()
            messages.success(request, "FD Product created successfully!")
            return redirect("fd_product_list")
    else:
        form = FDProductForm()
    
    return render(request, "fixed_deposit/fd_product_form.html", {"form": form, "title": "Create FD Product"})


@require_fixed_deposit_feature
def fd_product_edit(request, uuid):
    """Edit FD Product"""
    product = get_object_or_404(FDProduct, uuid=uuid)
    
    if request.method == "POST":
        form = FDProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "FD Product updated successfully!")
            return redirect("fd_product_list")
    else:
        form = FDProductForm(instance=product)
    
    return render(request, "fixed_deposit/fd_product_form.html", {"form": form, "title": "Edit FD Product"})


@require_fixed_deposit_feature
def fd_interest_accrual_report(request):
    """View interest accrual report"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    
    accruals = FDInterestAccrual.objects.filter(branch_id__in=branch_ids).select_related('fixed_deposit')
    
    return render(request, "fixed_deposit/interest_accrual_report.html", {"accruals": accruals})


@require_fixed_deposit_feature
def run_daily_interest_accrual(request):
    """Run daily interest accrual for all active FDs (admin/scheduled task)"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    
    active_fds = FixedDeposit.objects.filter(status='active', branch_id__in=branch_ids)
    accrual_date = date.today()
    count = 0
    
    for fd in active_fds:
        # Check if already accrued for today
        if FDInterestAccrual.objects.filter(fixed_deposit=fd, accrual_date=accrual_date).exists():
            continue
        
        # Calculate daily accrued interest
        accrued_today = fd.calculate_accrued_interest(accrual_date)
        
        # Get previous cumulative
        last_accrual = FDInterestAccrual.objects.filter(fixed_deposit=fd).order_by('-accrual_date').first()
        prev_cumulative = last_accrual.cumulative_accrued if last_accrual else Decimal("0.00")
        
        # Calculate today's portion
        if last_accrual:
            daily_amount = accrued_today - prev_cumulative
        else:
            daily_amount = accrued_today
        
        FDInterestAccrual.objects.create(
            fixed_deposit=fd,
            branch=fd.branch,
            accrual_date=accrual_date,
            opening_principal=fd.deposit_amount,
            interest_rate=fd.interest_rate,
            days_in_period=1,
            accrued_amount=daily_amount,
            cumulative_accrued=accrued_today,
        )
        count += 1
    
    messages.success(request, f"Interest accrual completed for {count} Fixed Deposits.")
    return redirect("fd_interest_accrual_report")


@require_fixed_deposit_feature
def fd_maturity_report(request):
    """Report of FDs maturing soon"""
    from accounts.utils import get_company_branch_ids
    from datetime import timedelta
    branch_ids = get_company_branch_ids(request.user)
    
    today = date.today()
    next_30_days = today + timedelta(days=30)
    
    maturing_fds = FixedDeposit.objects.filter(
        status='active',
        branch_id__in=branch_ids,
        maturity_date__gte=today,
        maturity_date__lte=next_30_days
    ).order_by('maturity_date')
    
    matured_fds = FixedDeposit.objects.filter(
        status='active',
        branch_id__in=branch_ids,
        maturity_date__lt=today
    ).order_by('maturity_date')
    
    return render(request, "fixed_deposit/fd_maturity_report.html", {
        "maturing_fds": maturing_fds,
        "matured_fds": matured_fds,
        "today": today,
    })


@require_fixed_deposit_feature
def auto_renew_matured_fds(request):
    """Auto-renew matured FDs that have auto_renewal enabled"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    
    today = date.today()
    
    # Get matured FDs with auto-renewal enabled
    matured_fds = FixedDeposit.objects.filter(
        status='active',
        branch_id__in=branch_ids,
        maturity_date__lt=today,
        auto_renewal=True
    )
    
    renewed_count = 0
    
    for fd in matured_fds:
        try:
            with transaction.atomic():
                # Create renewal history
                FDRenewalHistory.objects.create(
                    original_fd=fd,
                    branch=fd.branch,
                    renewal_date=today,
                    original_principal=fd.deposit_amount,
                    interest_earned=fd.interest_amount,
                    renewal_type='principal_interest',
                    renewed_principal=fd.maturity_amount,
                    new_tenure_months=fd.tenure_months,
                    new_interest_rate=fd.interest_rate,
                    is_auto_renewal=True,
                    remarks="Auto-renewed at maturity",
                    created_by="SYSTEM"
                )
                
                # Update old FD
                fd.status = 'renewed'
                fd.save()
                
                # Create new FD
                FixedDeposit.objects.create(
                    customer=fd.customer,
                    cust_gl_no=fd.cust_gl_no,
                    cust_ac_no=fd.cust_ac_no,
                    fixed_gl_no=fd.fixed_gl_no,
                    fixed_ac_no=fd.fixed_ac_no,
                    branch=fd.branch,
                    deposit_amount=fd.maturity_amount,
                    interest_rate=fd.interest_rate,
                    tenure_months=fd.tenure_months,
                    start_date=today,
                    maturity_date=today + timedelta(days=fd.tenure_months * 30),
                    interest_type=fd.interest_type,
                    compound_frequency=fd.compound_frequency,
                    auto_renewal=True,
                    original_fd=fd,
                    renewal_count=fd.renewal_count + 1,
                    nominee_name=fd.nominee_name,
                    nominee_relationship=fd.nominee_relationship,
                    created_by="SYSTEM",
                    cycle=fd.cycle + 1 if fd.cycle else 1,
                )
                
                renewed_count += 1
                
        except Exception as e:
            logger.error(f"Error auto-renewing FD {fd.fixed_ac_no}: {e}")
    
    messages.success(request, f"Auto-renewed {renewed_count} Fixed Deposits.")
    return redirect("fd_maturity_report")
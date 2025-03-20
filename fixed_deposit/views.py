from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from .models import FixedDeposit
from customers.models import FixedDepositAccount, Customer
from transactions.models import Memtrans
from .forms import FixedDepositForm

from customers.models import Customer



def display_customers_with_fixed_deposit(request):
    customers = Customer.objects.filter(gl_no__startswith="206").select_related("branch")
    fixed_accounts = FixedDepositAccount.objects.select_related("customer")

    return render(request, "fixed_deposit/customers_list.html", {
        "customers": customers,
        "fixed_accounts": fixed_accounts
    })



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

    return render(request, "fixed_deposit/fixed_deposit_form.html", {
        "form": form,
        "customer": customer,
        "customers": Customer.objects.all(),
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

def withdraw_fixed_deposit(request, deposit_id):
    fixed_deposit = get_object_or_404(FixedDeposit, id=deposit_id)

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

def running_fixed_deposits(request):
    """Fetch and display all currently active fixed deposits."""
    running_deposits = FixedDeposit.objects.filter(start_date__lte=now(), maturity_date__gte=now())

    return render(request, "fixed_deposit/running_fixed_deposits.html", {
        "running_deposits": running_deposits
    })







from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.utils.timezone import now
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

def reversal_for_fixed_deposit(request, deposit_id):
    fixed_deposit = get_object_or_404(FixedDeposit, id=deposit_id)

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

def reversal_fixed_deposit_list(request):
    fixed_deposits = FixedDeposit.objects.filter(status="active")
    print(f"Found {fixed_deposits.count()} active deposits")  # Debugging line
    return render(request, "fixed_deposit/reverse_fixed_deposit_list.html", {"fixed_deposits": fixed_deposits})


def fixed_dep(request):
    return render(request, 'fixed_deposit/fixed_dep.html')
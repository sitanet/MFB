from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import FixedAsset
from .forms import FixedAssetForm
from company.models import Branch
from decimal import Decimal

# View for listing assets
def asset_list(request):
    assets = FixedAsset.objects.filter(is_disposed=False)
    for asset in assets:
        asset.nbv = asset.net_book_value  # ✅ Access it as a property, without parentheses
    return render(request, 'assets/asset_list.html', {'assets': assets})

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import FixedAsset, AssetType, AssetGroup, Branch, Department, Officer, AssetLocation, AssetClass, DepreciationMethod
from accounts_admin.models import Account
from .forms import FixedAssetForm
from transactions.models import Memtrans
from transactions.utils import generate_fixed_asset_id

def asset_create(request):
    if request.method == "POST":
        try:
            # Manually handling form data
            asset_name = request.POST.get("asset_name")
            asset_type_id = request.POST.get("asset_type")
            asset_group_id = request.POST.get("asset_group")
            branch_id = request.POST.get("branch")
            gl_account_id = request.POST.get("gl_account_id")  # This is a string, we need to convert it
            ac_no = request.POST.get("ac_no")
            asset_id = request.POST.get("asset_id")
            asset_serial_no = request.POST.get("asset_serial_no")
            asset_model_no = request.POST.get("asset_model_no")
            asset_class_id = request.POST.get("asset_class")
            asset_location_id = request.POST.get("asset_locations")
            department_id = request.POST.get("department")
            officer_id = request.POST.get("officer")
            date_of_purchase = request.POST.get("date_of_purchase")
            assigned_date = request.POST.get("assigned_date") or None
            asset_cost = request.POST.get("asset_cost")
            bank_account_id = request.POST.get("bank_account")
            allowance_account_id = request.POST.get("allowance_account")
            expense_account_id = request.POST.get("expense_account")
            asset_life_months = request.POST.get("asset_life_months")
            minimum_asset_cost = request.POST.get("minimum_asset_cost")
            residual_value = request.POST.get("residual_value")
            depreciation_method_id = request.POST.get("depreciation_method")
            depreciation_rate = request.POST.get("depreciation_rate")
            depreciation_frequency = request.POST.get("depreciation_frequency")

            # Ensure all required fields are filled
            if not all([asset_name, asset_type_id, asset_group_id, branch_id, gl_account_id, asset_cost, bank_account_id]):
                messages.error(request, "Please fill in all required fields.")
                return redirect("asset_create")

            # 🔹 Fetch Account instances instead of using string IDs
            gl_account = Account.objects.get(id=int(gl_account_id))  # Convert ID to instance
            bank_account = Account.objects.get(id=int(bank_account_id))  # Convert ID to instance
            allowance_account = Account.objects.get(id=int(allowance_account_id)) if allowance_account_id else None
            expense_account = Account.objects.get(id=int(expense_account_id)) if expense_account_id else None

            # Create Fixed Asset
            asset = FixedAsset.objects.create(
                asset_name=asset_name,
                asset_type_id=asset_type_id,
                asset_group_id=asset_group_id,
                branch_id=branch_id,
                gl_account=gl_account,  # Assigning an instance
                ac_no=ac_no,
                asset_id=asset_id,
                asset_serial_no=asset_serial_no,
                asset_model_no=asset_model_no,
                asset_class_id=asset_class_id,
                asset_location_id=asset_location_id,
                department_id=department_id,
                officer_id=officer_id,
                date_of_purchase=date_of_purchase,
                assigned_date=assigned_date,
                asset_cost=asset_cost,
                bank_account=bank_account,  # Assigning an instance
                allowance_account=allowance_account,  # Assigning an instance
                expense_account=expense_account,  # Assigning an instance
                asset_life_months=asset_life_months,
                minimum_asset_cost=minimum_asset_cost,
                residual_value=residual_value,
                depreciation_method_id=depreciation_method_id,
                depreciation_rate=depreciation_rate,
                depreciation_frequency=depreciation_frequency
            )

            # Generate transaction number
            trx_no = generate_fixed_asset_id()[:10]

            # Create Debit Entry (Dr - Fixed Asset)
            Memtrans.objects.create(
                branch=asset.bank_account.branch,
                customer=None,
                loans=None,
                cycle=1,
                gl_no=asset.gl_account.id,  # Fixed Asset GL Account
                ac_no=asset.bank_account.id,  # Debit (Asset Account)
                trx_no=trx_no,
                ses_date=asset.date_of_purchase,
                app_date=timezone.now().date(),
                amount=asset.asset_cost,
                description=f"Asset Purchase - {asset.asset_name}",
                error='A',
                type='D',  # Debit
                account_type='A',
                code='FA',  # Fixed Asset Code
                user=request.user
            )

            # Create Credit Entry (Cr - Bank)
            Memtrans.objects.create(
                branch=asset.bank_account.branch,
                customer=None,
                loans=None,
                cycle=1,
                gl_no=asset.bank_account.id,  # Bank GL
                ac_no=asset.bank_account.id,
                trx_no=trx_no,  
                ses_date=asset.date_of_purchase,
                app_date=timezone.now().date(),
                amount=asset.asset_cost,
                description=f"Asset Payment - {asset.asset_name}",
                error='A',
                type='C',  # Credit
                account_type='B',  # Bank Account
                code='FA',
                user=request.user
            )

            messages.success(request, "Asset registered and transactions recorded successfully!")
            return redirect("asset_list")

        except Account.DoesNotExist:
            messages.error(request, "One or more accounts could not be found.")
            return redirect("asset_create")

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect("asset_create")

    # Querying required dropdown fields
    context = {
        "asset_types": AssetType.objects.all(),
        "asset_groups": AssetGroup.objects.all(),
        "branches": Branch.objects.all(),
        "departments": Department.objects.all(),
        "officers": Officer.objects.all(),
        "asset_classes": AssetClass.objects.all(),
        "asset_locations": AssetLocation.objects.all(),
        "depreciation_methods": DepreciationMethod.objects.all(),
        "gl_accounts": Account.objects.all(),
        "bank_accounts": Account.objects.all(),
        "allowance_accounts": Account.objects.all(),
        "expense_accounts": Account.objects.all(),
        "asset_class": AssetClass.objects.all(),
    }

    return render(request, "assets/asset_form.html", context)

# View for deleting an asset
def asset_delete(request, asset_id):
    asset = get_object_or_404(FixedAsset, id=asset_id)
    if request.method == "POST":
        asset.delete()
        messages.success(request, "Asset deleted successfully!")
        return redirect('asset_list')
    return render(request, 'assets/asset_confirm_delete.html', {'asset': asset})


from django.shortcuts import render, get_object_or_404, redirect
from .models import FixedAsset
from .forms import FixedAssetForm

def asset_update(request, asset_id):
    asset = get_object_or_404(FixedAsset, id=asset_id)
    
    if request.method == "POST":
        form = FixedAssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            return redirect("asset_list")  # Redirect after update
    else:
        form = FixedAssetForm(instance=asset)

    return render(request, "assets/asset_form.html", {"form": form, "asset": asset})



from decimal import Decimal
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from datetime import timedelta
from dateutil.relativedelta import relativedelta  # Helps with month calculations
from .models import FixedAsset, AssetTransaction
from transactions.utils import generate_fixed_asset_dep_id

from company.models import Branch

def post_depreciation(request, asset_id):
    """
    Handles depreciation posting while preventing duplicate entries on the same day
    and ensuring it follows the asset’s depreciation frequency.
    """
    asset = get_object_or_404(FixedAsset, id=asset_id)
    branch = asset.branch  # Get the branch associated with the asset
    session_date = branch.session_date if branch.session_date else timezone.now().date()

    # Retrieve the last depreciation transaction
    last_depreciation = AssetTransaction.objects.filter(
        asset=asset, transaction_type="Depreciation"
    ).order_by('-transaction_date').first()

    # Calculate the next allowed depreciation date
    if last_depreciation:
        last_date = last_depreciation.transaction_date
        if asset.depreciation_frequency == '12':  # Monthly
            next_allowed_date = last_date + relativedelta(months=1)
        elif asset.depreciation_frequency == '4':  # Quarterly
            next_allowed_date = last_date + relativedelta(months=3)
        elif asset.depreciation_frequency == '2':  # Semi-Annually
            next_allowed_date = last_date + relativedelta(months=6)
        elif asset.depreciation_frequency == '1':  # Annually
            next_allowed_date = last_date + relativedelta(years=1)
        else:
            messages.error(request, "Invalid depreciation frequency.")
            return redirect('asset_list')

        # Prevent depreciation if it's too early (using session_date)
        if session_date < next_allowed_date:
            messages.warning(request, f"Depreciation for {asset.asset_name} can only be posted after {next_allowed_date}.")
            return redirect('asset_list')

    # Ensure valid depreciation period
    if asset.asset_life_months <= 0:
        messages.error(request, f"Asset '{asset.asset_name}' has an invalid depreciation life.")
        return redirect('asset_list')

    # Calculate monthly depreciation
    monthly_depreciation = (asset.asset_cost - asset.residual_value) / Decimal(asset.asset_life_months)

    # Prevent over-depreciation
    depreciation_amount = min(monthly_depreciation, asset.net_book_value - asset.residual_value)

    if depreciation_amount > 0:
        # Update total depreciation
        asset.total_depreciation += depreciation_amount
        asset.save()

        # Record the depreciation transaction in AssetTransaction
        AssetTransaction.objects.create(
            asset=asset,
            transaction_date=session_date,  # Use session date instead of today
            transaction_type="Depreciation",
            transaction_amount=depreciation_amount,
            description=f"Depreciation recorded for {asset.asset_name}"
        )

        # Generate transaction number
        trx_no = generate_fixed_asset_dep_id()[:10]

        # Debit Depreciation Expense
        Memtrans.objects.create(
            branch=branch,  
            customer=None,
            loans=None,
            cycle=1,
            gl_no=asset.expense_account.id,  # Expense GL
            ac_no=asset.allowance_account.id,  # Accumulated Depreciation
            trx_no=trx_no,
            ses_date=session_date,  # Use branch session date
            app_date=session_date,
            amount=depreciation_amount,
            description=f"Depreciation for {asset.asset_name}",
            error='A',
            type='D',  # Debit
            account_type='E',  # Expense Account
            code='DEP',
            user=request.user
        )

        # Credit Accumulated Depreciation
        Memtrans.objects.create(
            branch=branch,
            customer=None,
            loans=None,
            cycle=1,
            gl_no=asset.allowance_account.id,  # Accumulated Depreciation GL
            ac_no=asset.expense_account.id,  # Expense Account
            trx_no=trx_no,
            ses_date=session_date,  # Use branch session date
            app_date=session_date,
            amount=depreciation_amount,
            description=f"Accumulated Depreciation for {asset.asset_name}",
            error='A',
            type='C',  # Credit
            account_type='L',  # Liability (Accumulated Depreciation)
            code='DEP',
            user=request.user
        )

        messages.success(request, f"Depreciation of ${depreciation_amount} posted for {asset.asset_name}.")
    else:
        messages.warning(request, f"No depreciation required for {asset.asset_name} this period.")

    return redirect('asset_list')





def post_all_depreciation(request):
    """
    Posts depreciation for all assets due on the session date and generates a report.
    """
    branches = Branch.objects.all()
    depreciated_assets = []  # Store depreciated assets for the report

    for branch in branches:
        session_date = branch.session_date if branch.session_date else timezone.now().date()
        
        assets = FixedAsset.objects.filter(branch=branch)
        for asset in assets:
            last_depreciation = AssetTransaction.objects.filter(
                asset=asset, transaction_type="Depreciation"
            ).order_by('-transaction_date').first()

            if last_depreciation:
                last_date = last_depreciation.transaction_date
                if asset.depreciation_frequency == '12':  # Monthly
                    next_allowed_date = last_date + relativedelta(months=1)
                elif asset.depreciation_frequency == '4':  # Quarterly
                    next_allowed_date = last_date + relativedelta(months=3)
                elif asset.depreciation_frequency == '2':  # Semi-Annually
                    next_allowed_date = last_date + relativedelta(months=6)
                elif asset.depreciation_frequency == '1':  # Annually
                    next_allowed_date = last_date + relativedelta(years=1)
                else:
                    continue  # Skip invalid frequency

                if session_date < next_allowed_date:
                    continue  # Skip if depreciation is not yet due

            if asset.asset_life_months <= 0 or asset.net_book_value <= asset.residual_value:
                continue  # Skip invalid assets
            
            depreciation_amount = min(
                (asset.asset_cost - asset.residual_value) / Decimal(asset.asset_life_months),
                asset.net_book_value - asset.residual_value
            )
            
            if depreciation_amount > 0:
                asset.total_depreciation += depreciation_amount
                asset.save()
                
                # Save asset depreciation transaction
                AssetTransaction.objects.create(
                    asset=asset,
                    transaction_date=session_date,
                    transaction_type="Depreciation",
                    transaction_amount=depreciation_amount,
                    description=f"Depreciation recorded for {asset.asset_name}"
                )

                trx_no = generate_fixed_asset_dep_id()[:10]

                # Create double-entry transactions in Memtrans
                Memtrans.objects.create(
                    branch=branch,
                    customer=None,
                    loans=None,
                    cycle=1,
                    gl_no=asset.expense_account.id,
                    ac_no=asset.allowance_account.id,
                    trx_no=trx_no,
                    ses_date=session_date,
                    app_date=session_date,
                    amount=depreciation_amount,
                    description=f"Depreciation for {asset.asset_name}",
                    error='A',
                    type='D',
                    account_type='E',
                    code='DEP',
                    user=request.user
                )
                
                Memtrans.objects.create(
                    branch=branch,
                    customer=None,
                    loans=None,
                    cycle=1,
                    gl_no=asset.allowance_account.id,
                    ac_no=asset.expense_account.id,
                    trx_no=trx_no,
                    ses_date=session_date,
                    app_date=session_date,
                    amount=depreciation_amount,
                    description=f"Accumulated Depreciation for {asset.asset_name}",
                    error='A',
                    type='C',
                    account_type='L',
                    code='DEP',
                    user=request.user
                )

                # Store the depreciated asset details for reporting
                depreciated_assets.append({
                    'asset_name': asset.asset_name,
                    'depreciation_amount': depreciation_amount,
                    'transaction_date': session_date,
                    'branch': branch.branch_name
                })

    if depreciated_assets:
        return render(request, 'assets/depreciation_report.html', {'depreciated_assets': depreciated_assets})
    else:
        messages.info(request, "No assets were due for depreciation.")
        return redirect('asset_list')




def fixed_asset_dash(request):
    return render(request, 'assets/fixed_asset_dash.html')




from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import FixedAsset, AssetDisposal
from transactions.models import Memtrans

def dispose_fixed_asset(request, asset_id):
    asset = get_object_or_404(FixedAsset, id=asset_id)

    if request.method == "POST":
        disposal_price = Decimal(request.POST.get("disposal_price"))
        disposal_reason = request.POST.get("disposal_reason")

        try:
            # ✅ Ensure asset is not already disposed
            if asset.is_disposed:
                messages.error(request, "This asset has already been disposed.")
                return redirect("asset_list")

            # ✅ Record disposal in AssetDisposal model
            AssetDisposal.objects.create(
                asset=asset,
                disposal_price=disposal_price,
                disposal_reason=disposal_reason,
            )

            # ✅ Debit Asset Disposal Account
            Memtrans.objects.create(
                branch=asset.branch,
                gl_no=asset.gl_account.gl_no,  # ✅ Corrected reference
                ac_no=asset.ac_no,  # ✅ ac_no comes directly from FixedAsset
                trx_no=f"DISP{asset.id}",
                ses_date=timezone.now().date(),
                amount=disposal_price,
                description=f"Disposal of {asset.asset_name}",
                type="D",  # Debit entry
            )

            # ✅ Credit Bank Account
            Memtrans.objects.create(
                branch=asset.branch,
                gl_no=asset.bank_account.gl_no,  # ✅ Corrected reference
                ac_no=asset.ac_no,  # ✅ ac_no remains the same
                trx_no=f"DISP{asset.id}",
                ses_date=timezone.now().date(),
                amount=disposal_price,
                description=f"Asset Disposal - {asset.asset_name}",
                type="C",  # Credit entry
            )

            # ✅ Mark asset as disposed
            asset.is_disposed = True
            asset.save()

            messages.success(request, f"Asset {asset.asset_name} disposed successfully!")
            return redirect("asset_list")

        except Exception as e:
            messages.error(request, f"Error disposing asset: {e}")

    return render(request, "assets/dispose_asset.html", {"asset": asset})



from .models import FixedAsset

def asset_detail(request, asset_id):
    asset = get_object_or_404(FixedAsset, id=asset_id)  # Fetch the asset or return 404 if not found
    return render(request, 'assets/asset_detail.html', {'asset': asset})



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
from .models import FixedAsset, AssetRevaluation
from .forms import AssetRevaluationForm

def revalue_asset(request, asset_id):
    asset = get_object_or_404(FixedAsset, pk=asset_id)

    # Calculate total depreciation and Net Book Value (NBV)
    total_depreciated = getattr(asset, "total_depreciation", Decimal("0.00"))
    net_book_value = asset.asset_cost - total_depreciated

    if request.method == "POST":
        form = AssetRevaluationForm(request.POST)
        if form.is_valid():
            new_value = form.cleaned_data["new_value"]
            new_residual = form.cleaned_data["new_residual"]
            reason = form.cleaned_data["reason"]

            # Ensure new value is not lower than total depreciation
            if new_value < total_depreciated:
                messages.error(request, "New asset value cannot be lower than total depreciation.")
                return redirect("revalue_asset", asset_id=asset.id)

            # Create revaluation entry
            AssetRevaluation.objects.create(
                asset=asset,
                previous_value=asset.asset_cost,
                new_value=new_value,
                previous_residual=asset.residual_value,
                new_residual=new_residual,
                reason=reason,
            )

            # Update asset values
            asset.asset_cost = new_value
            asset.residual_value = new_residual
            asset.save()

            messages.success(request, f"Asset {asset.asset_name} successfully revalued.")
            return redirect("asset_detail", asset_id=asset.id)
    else:
        form = AssetRevaluationForm(initial={
            "new_value": asset.asset_cost, 
            "new_residual": asset.residual_value
        })

    return render(request, "assets/revalue_asset.html", {
        "form": form, 
        "asset": asset, 
        "total_depreciated": total_depreciated,
        "net_book_value": net_book_value
    })

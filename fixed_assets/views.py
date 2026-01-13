from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import FixedAsset
from .forms import FixedAssetForm
from company.models import Branch
from decimal import Decimal
from functools import wraps


def require_fixed_assets_feature(view_func):
    """Decorator to check if branch has Fixed Assets feature enabled"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if hasattr(request.user, 'branch') and request.user.branch:
            if not request.user.branch.can_fixed_assets:
                messages.error(request, "Fixed Assets feature is not enabled for your branch. Please contact administrator.")
                return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_fixed_assets_feature
def asset_list(request):
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    assets = FixedAsset.objects.filter(is_disposed=False, branch_id__in=branch_ids)
    for asset in assets:
        asset.nbv = asset.net_book_value  # Access it as a property
    return render(request, 'assets/asset_list.html', {'assets': assets})

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import FixedAsset, AssetType, AssetGroup, Branch, Department, Officer, AssetLocation, AssetClass, DepreciationMethod
from accounts_admin.models import Account
from .forms import FixedAssetForm
from transactions.models import Memtrans
from transactions.utils import generate_fixed_asset_id


@require_fixed_assets_feature
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

    # Querying required dropdown fields - filter by company
    from accounts.utils import get_branch_from_vendor_db
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    user_company = user_branch.company if user_branch else None
    
    if user_branch and user_branch.head_office:
        ctx_branches = Branch.objects.filter(company=user_company)
    elif user_branch:
        ctx_branches = Branch.objects.filter(id=user_branch.id)
    else:
        ctx_branches = []
    
    context = {
        "asset_types": AssetType.objects.all(),
        "asset_groups": AssetGroup.objects.all(),
        "branches": ctx_branches,
        "departments": Department.objects.all(),
        "officers": Officer.objects.all(),
        "asset_classes": AssetClass.objects.all(),
        "asset_locations": AssetLocation.objects.all(),
        "depreciation_methods": DepreciationMethod.objects.all(),
        "gl_accounts": Account.all_objects.filter(branch__company=user_company) if user_company else [],
        "bank_accounts": Account.all_objects.filter(branch__company=user_company) if user_company else [],
        "allowance_accounts": Account.all_objects.filter(branch__company=user_company) if user_company else [],
        "expense_accounts": Account.all_objects.filter(branch__company=user_company) if user_company else [],
        "asset_class": AssetClass.objects.all(),
    }

    return render(request, "assets/asset_form.html", context)

@require_fixed_assets_feature
def asset_delete(request, uuid):
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    if request.method == "POST":
        asset.delete()
        messages.success(request, "Asset deleted successfully!")
        return redirect('asset_list')
    return render(request, 'assets/asset_confirm_delete.html', {'asset': asset})


from django.shortcuts import render, get_object_or_404, redirect
from .models import FixedAsset
from .forms import FixedAssetForm


@require_fixed_assets_feature
def asset_update(request, uuid):
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    
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


@require_fixed_assets_feature
def post_depreciation(request, uuid):
    """
    Handles depreciation posting while preventing duplicate entries on the same day
    and ensuring it follows the asset’s depreciation frequency.
    """
    asset = get_object_or_404(FixedAsset, uuid=uuid)
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





@require_fixed_assets_feature
def post_all_depreciation(request):
    """
    Posts depreciation for all assets due on the session date and generates a report.
    """
    from accounts.utils import get_branch_from_vendor_db
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    if not user_branch:
        messages.error(request, 'No branch assigned to user.')
        return redirect('dashboard')
    # Filter branches by company
    if user_branch.head_office:
        branches = Branch.objects.filter(company=user_branch.company)
    else:
        branches = Branch.objects.filter(id=user_branch.id)
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




@require_fixed_assets_feature
def fixed_asset_dash(request):
    return render(request, 'assets/fixed_asset_dash.html')




from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import FixedAsset, AssetDisposal
from transactions.models import Memtrans


@require_fixed_assets_feature
def dispose_fixed_asset(request, uuid):
    asset = get_object_or_404(FixedAsset, uuid=uuid)

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


@require_fixed_assets_feature
def asset_detail(request, uuid):
    asset = get_object_or_404(FixedAsset, uuid=uuid)  # Fetch the asset or return 404 if not found
    return render(request, 'assets/asset_detail.html', {'asset': asset})



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
from .models import FixedAsset, AssetRevaluation
from .forms import AssetRevaluationForm


@require_fixed_assets_feature
def revalue_asset(request, uuid):
    asset = get_object_or_404(FixedAsset, uuid=uuid)

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


# ==================== ASSET TRANSFER ====================

from .models import AssetTransfer, AssetImpairment, AssetInsurance, AssetMaintenance, AssetWarranty, AssetVerification


@require_fixed_assets_feature
def asset_transfer(request, uuid):
    """Transfer asset to different branch/department/location/officer"""
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    
    from accounts.utils import get_branch_from_vendor_db
    user_branch = get_branch_from_vendor_db(request.user.branch_id)
    user_company = user_branch.company if user_branch else None
    
    if request.method == "POST":
        try:
            transfer = AssetTransfer.objects.create(
                asset=asset,
                transfer_date=request.POST.get('transfer_date') or timezone.now().date(),
                from_branch=asset.branch,
                from_department=asset.department,
                from_location=asset.asset_location,
                from_officer=asset.officer,
                to_branch_id=request.POST.get('to_branch') or None,
                to_department_id=request.POST.get('to_department') or None,
                to_location_id=request.POST.get('to_location') or None,
                to_officer_id=request.POST.get('to_officer') or None,
                reason=request.POST.get('reason', ''),
                approved_by=request.POST.get('approved_by', ''),
            )
            messages.success(request, f"Asset {asset.asset_name} transferred successfully!")
            return redirect('asset_detail', uuid=asset.uuid)
        except Exception as e:
            messages.error(request, f"Error transferring asset: {e}")
    
    context = {
        'asset': asset,
        'branches': Branch.objects.filter(company=user_company) if user_company else [],
        'departments': Department.objects.all(),
        'locations': AssetLocation.objects.all(),
        'officers': Officer.objects.all(),
    }
    return render(request, 'assets/asset_transfer_form.html', context)


@require_fixed_assets_feature
def asset_transfer_history(request, uuid):
    """View transfer history for an asset"""
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    transfers = asset.transfers.all().order_by('-transfer_date')
    return render(request, 'assets/asset_transfer_history.html', {'asset': asset, 'transfers': transfers})


# ==================== ASSET IMPAIRMENT ====================

@require_fixed_assets_feature
def asset_impairment(request, uuid):
    """Record impairment loss for an asset"""
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    
    if request.method == "POST":
        try:
            impairment_loss = Decimal(request.POST.get('impairment_loss', '0'))
            previous_nbv = asset.net_book_value
            new_nbv = previous_nbv - impairment_loss
            
            if impairment_loss <= 0:
                messages.error(request, "Impairment loss must be greater than zero.")
                return redirect('asset_impairment', uuid=uuid)
            
            if new_nbv < asset.residual_value:
                messages.error(request, "Impairment cannot reduce NBV below residual value.")
                return redirect('asset_impairment', uuid=uuid)
            
            AssetImpairment.objects.create(
                asset=asset,
                impairment_date=request.POST.get('impairment_date') or timezone.now().date(),
                previous_nbv=previous_nbv,
                impairment_loss=impairment_loss,
                new_nbv=new_nbv,
                reason=request.POST.get('reason', ''),
                approved_by=request.POST.get('approved_by', ''),
            )
            messages.success(request, f"Impairment of {impairment_loss} recorded for {asset.asset_name}.")
            return redirect('asset_detail', uuid=asset.uuid)
        except Exception as e:
            messages.error(request, f"Error recording impairment: {e}")
    
    return render(request, 'assets/asset_impairment_form.html', {'asset': asset})


# ==================== ASSET INSURANCE ====================

@require_fixed_assets_feature
def asset_insurance_list(request):
    """List all asset insurance policies"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    
    insurances = AssetInsurance.objects.filter(asset__branch_id__in=branch_ids).select_related('asset')
    return render(request, 'assets/asset_insurance_list.html', {'insurances': insurances})


@require_fixed_assets_feature
def asset_insurance_add(request, uuid):
    """Add insurance policy for an asset"""
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    
    if request.method == "POST":
        try:
            AssetInsurance.objects.create(
                asset=asset,
                policy_number=request.POST.get('policy_number'),
                insurance_company=request.POST.get('insurance_company'),
                coverage_type=request.POST.get('coverage_type'),
                coverage_amount=Decimal(request.POST.get('coverage_amount', '0')),
                premium_amount=Decimal(request.POST.get('premium_amount', '0')),
                start_date=request.POST.get('start_date'),
                expiry_date=request.POST.get('expiry_date'),
                contact_person=request.POST.get('contact_person', ''),
                contact_phone=request.POST.get('contact_phone', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, f"Insurance policy added for {asset.asset_name}.")
            return redirect('asset_detail', uuid=asset.uuid)
        except Exception as e:
            messages.error(request, f"Error adding insurance: {e}")
    
    return render(request, 'assets/asset_insurance_form.html', {'asset': asset})


# ==================== ASSET MAINTENANCE ====================

@require_fixed_assets_feature
def asset_maintenance_list(request):
    """List all maintenance records"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    
    maintenances = AssetMaintenance.objects.filter(asset__branch_id__in=branch_ids).select_related('asset')
    return render(request, 'assets/asset_maintenance_list.html', {'maintenances': maintenances})


@require_fixed_assets_feature
def asset_maintenance_add(request, uuid):
    """Add maintenance record for an asset"""
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    
    if request.method == "POST":
        try:
            AssetMaintenance.objects.create(
                asset=asset,
                maintenance_type=request.POST.get('maintenance_type'),
                maintenance_date=request.POST.get('maintenance_date'),
                next_maintenance_date=request.POST.get('next_maintenance_date') or None,
                description=request.POST.get('description'),
                performed_by=request.POST.get('performed_by'),
                cost=Decimal(request.POST.get('cost', '0')),
                parts_replaced=request.POST.get('parts_replaced', ''),
                status=request.POST.get('status', 'completed'),
                invoice_number=request.POST.get('invoice_number', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, f"Maintenance record added for {asset.asset_name}.")
            return redirect('asset_detail', uuid=asset.uuid)
        except Exception as e:
            messages.error(request, f"Error adding maintenance: {e}")
    
    return render(request, 'assets/asset_maintenance_form.html', {'asset': asset})


# ==================== ASSET WARRANTY ====================

@require_fixed_assets_feature  
def asset_warranty_list(request):
    """List all warranty records"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    
    warranties = AssetWarranty.objects.filter(asset__branch_id__in=branch_ids).select_related('asset')
    return render(request, 'assets/asset_warranty_list.html', {'warranties': warranties})


@require_fixed_assets_feature
def asset_warranty_add(request, uuid):
    """Add warranty for an asset"""
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    
    if request.method == "POST":
        try:
            AssetWarranty.objects.create(
                asset=asset,
                warranty_provider=request.POST.get('warranty_provider'),
                warranty_type=request.POST.get('warranty_type'),
                start_date=request.POST.get('start_date'),
                expiry_date=request.POST.get('expiry_date'),
                coverage_details=request.POST.get('coverage_details'),
                terms_and_conditions=request.POST.get('terms_and_conditions', ''),
                contact_person=request.POST.get('contact_person', ''),
                contact_phone=request.POST.get('contact_phone', ''),
                contact_email=request.POST.get('contact_email', ''),
            )
            messages.success(request, f"Warranty added for {asset.asset_name}.")
            return redirect('asset_detail', uuid=asset.uuid)
        except Exception as e:
            messages.error(request, f"Error adding warranty: {e}")
    
    return render(request, 'assets/asset_warranty_form.html', {'asset': asset})


# ==================== ASSET VERIFICATION ====================

@require_fixed_assets_feature
def asset_verification_list(request):
    """List all verification records"""
    from accounts.utils import get_company_branch_ids
    branch_ids = get_company_branch_ids(request.user)
    
    verifications = AssetVerification.objects.filter(asset__branch_id__in=branch_ids).select_related('asset')
    return render(request, 'assets/asset_verification_list.html', {'verifications': verifications})


@require_fixed_assets_feature
def asset_verification_add(request, uuid):
    """Add verification record for an asset"""
    asset = get_object_or_404(FixedAsset, uuid=uuid)
    
    if request.method == "POST":
        try:
            AssetVerification.objects.create(
                asset=asset,
                verification_date=request.POST.get('verification_date'),
                verified_by=request.POST.get('verified_by'),
                status=request.POST.get('status'),
                physical_condition=request.POST.get('physical_condition', ''),
                actual_location_id=request.POST.get('actual_location') or None,
                remarks=request.POST.get('remarks', ''),
            )
            messages.success(request, f"Verification recorded for {asset.asset_name}.")
            return redirect('asset_detail', uuid=asset.uuid)
        except Exception as e:
            messages.error(request, f"Error recording verification: {e}")
    
    context = {
        'asset': asset,
        'locations': AssetLocation.objects.all(),
    }
    return render(request, 'assets/asset_verification_form.html', context)


# ==================== REPORTS ====================

@require_fixed_assets_feature
def depreciation_schedule_report(request):
    """Generate depreciation schedule report"""
    from accounts.utils import get_company_branch_ids
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    branch_ids = get_company_branch_ids(request.user)
    assets = FixedAsset.objects.filter(branch_id__in=branch_ids, is_disposed=False)
    
    schedule = []
    for asset in assets:
        if asset.asset_life_months <= 0:
            continue
            
        monthly_dep = (asset.asset_cost - asset.residual_value) / Decimal(asset.asset_life_months)
        remaining_life = max(0, asset.asset_life_months - int(asset.total_depreciation / monthly_dep) if monthly_dep > 0 else 0)
        
        # Project future depreciation
        projections = []
        current_nbv = asset.net_book_value
        current_date = date.today()
        
        for i in range(min(12, remaining_life)):  # Show next 12 periods max
            if current_nbv <= asset.residual_value:
                break
            dep_amount = min(monthly_dep, current_nbv - asset.residual_value)
            current_nbv -= dep_amount
            
            if asset.depreciation_frequency == '12':
                period_date = current_date + relativedelta(months=i+1)
            elif asset.depreciation_frequency == '4':
                period_date = current_date + relativedelta(months=(i+1)*3)
            elif asset.depreciation_frequency == '2':
                period_date = current_date + relativedelta(months=(i+1)*6)
            else:
                period_date = current_date + relativedelta(years=i+1)
            
            projections.append({
                'period': i + 1,
                'date': period_date,
                'depreciation': dep_amount,
                'nbv': current_nbv,
            })
        
        schedule.append({
            'asset': asset,
            'monthly_depreciation': monthly_dep,
            'remaining_life': remaining_life,
            'projections': projections,
        })
    
    return render(request, 'assets/depreciation_schedule_report.html', {'schedule': schedule})


@require_fixed_assets_feature
def asset_register_report(request):
    """Generate complete asset register report"""
    from accounts.utils import get_company_branch_ids
    from django.db.models import Sum
    
    branch_ids = get_company_branch_ids(request.user)
    assets = FixedAsset.objects.filter(branch_id__in=branch_ids).select_related(
        'asset_type', 'asset_group', 'branch', 'department', 'officer', 'asset_location'
    )
    
    # Summary statistics
    total_cost = assets.aggregate(total=Sum('asset_cost'))['total'] or Decimal('0')
    total_depreciation = assets.aggregate(total=Sum('total_depreciation'))['total'] or Decimal('0')
    total_nbv = total_cost - total_depreciation
    
    active_assets = assets.filter(is_disposed=False)
    disposed_assets = assets.filter(is_disposed=True)
    
    # Group by type
    by_type = {}
    for asset in active_assets:
        type_name = asset.asset_type.name
        if type_name not in by_type:
            by_type[type_name] = {'count': 0, 'cost': Decimal('0'), 'nbv': Decimal('0')}
        by_type[type_name]['count'] += 1
        by_type[type_name]['cost'] += asset.asset_cost
        by_type[type_name]['nbv'] += asset.net_book_value
    
    context = {
        'assets': active_assets,
        'disposed_assets': disposed_assets,
        'total_cost': total_cost,
        'total_depreciation': total_depreciation,
        'total_nbv': total_nbv,
        'by_type': by_type,
        'active_count': active_assets.count(),
        'disposed_count': disposed_assets.count(),
    }
    return render(request, 'assets/asset_register_report.html', context)


# ==================== ASSET CATEGORY CRUD ====================

@require_fixed_assets_feature
def asset_type_list(request):
    """List all asset types"""
    types = AssetType.objects.all()
    return render(request, 'assets/asset_type_list.html', {'types': types})


@require_fixed_assets_feature
def asset_type_create(request):
    """Create new asset type"""
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            AssetType.objects.create(name=name)
            messages.success(request, f"Asset Type '{name}' created.")
            return redirect('asset_type_list')
    return render(request, 'assets/asset_type_form.html', {'title': 'Create Asset Type'})


@require_fixed_assets_feature
def asset_type_edit(request, uuid):
    """Edit asset type"""
    asset_type = get_object_or_404(AssetType, uuid=uuid)
    if request.method == "POST":
        asset_type.name = request.POST.get('name')
        asset_type.save()
        messages.success(request, f"Asset Type updated.")
        return redirect('asset_type_list')
    return render(request, 'assets/asset_type_form.html', {'type': asset_type, 'title': 'Edit Asset Type'})


@require_fixed_assets_feature
def asset_type_delete(request, uuid):
    """Delete asset type"""
    asset_type = get_object_or_404(AssetType, uuid=uuid)
    if request.method == "POST":
        asset_type.delete()
        messages.success(request, "Asset Type deleted.")
        return redirect('asset_type_list')
    return render(request, 'assets/asset_type_confirm_delete.html', {'type': asset_type})


@require_fixed_assets_feature
def asset_group_list(request):
    """List all asset groups"""
    groups = AssetGroup.objects.all()
    return render(request, 'assets/asset_group_list.html', {'groups': groups})


@require_fixed_assets_feature
def asset_group_create(request):
    """Create new asset group"""
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            AssetGroup.objects.create(name=name)
            messages.success(request, f"Asset Group '{name}' created.")
            return redirect('asset_group_list')
    return render(request, 'assets/asset_group_form.html', {'title': 'Create Asset Group'})


@require_fixed_assets_feature
def asset_group_edit(request, uuid):
    """Edit asset group"""
    group = get_object_or_404(AssetGroup, uuid=uuid)
    if request.method == "POST":
        group.name = request.POST.get('name')
        group.save()
        messages.success(request, "Asset Group updated.")
        return redirect('asset_group_list')
    return render(request, 'assets/asset_group_form.html', {'group': group, 'title': 'Edit Asset Group'})


@require_fixed_assets_feature
def asset_location_list(request):
    """List all asset locations"""
    locations = AssetLocation.objects.all()
    return render(request, 'assets/asset_location_list.html', {'locations': locations})


@require_fixed_assets_feature
def asset_location_create(request):
    """Create new asset location"""
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            AssetLocation.objects.create(name=name)
            messages.success(request, f"Asset Location '{name}' created.")
            return redirect('asset_location_list')
    return render(request, 'assets/asset_location_form.html', {'title': 'Create Asset Location'})


@require_fixed_assets_feature
def asset_location_edit(request, uuid):
    """Edit asset location"""
    location = get_object_or_404(AssetLocation, uuid=uuid)
    if request.method == "POST":
        location.name = request.POST.get('name')
        location.save()
        messages.success(request, "Asset Location updated.")
        return redirect('asset_location_list')
    return render(request, 'assets/asset_location_form.html', {'location': location, 'title': 'Edit Asset Location'})


@require_fixed_assets_feature
def department_list(request):
    """List all departments"""
    departments = Department.objects.all()
    return render(request, 'assets/department_list.html', {'departments': departments})


@require_fixed_assets_feature
def department_create(request):
    """Create new department"""
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            Department.objects.create(name=name)
            messages.success(request, f"Department '{name}' created.")
            return redirect('department_list')
    return render(request, 'assets/department_form.html', {'title': 'Create Department'})


@require_fixed_assets_feature
def department_edit(request, uuid):
    """Edit department"""
    department = get_object_or_404(Department, uuid=uuid)
    if request.method == "POST":
        department.name = request.POST.get('name')
        department.save()
        messages.success(request, "Department updated.")
        return redirect('department_list')
    return render(request, 'assets/department_form.html', {'department': department, 'title': 'Edit Department'})


@require_fixed_assets_feature
def officer_list(request):
    """List all officers"""
    officers = Officer.objects.all()
    return render(request, 'assets/officer_list.html', {'officers': officers})


@require_fixed_assets_feature
def officer_create(request):
    """Create new officer"""
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            Officer.objects.create(name=name)
            messages.success(request, f"Officer '{name}' created.")
            return redirect('officer_list')
    return render(request, 'assets/officer_form.html', {'title': 'Create Officer'})


@require_fixed_assets_feature
def officer_edit(request, uuid):
    """Edit officer"""
    officer = get_object_or_404(Officer, uuid=uuid)
    if request.method == "POST":
        officer.name = request.POST.get('name')
        officer.save()
        messages.success(request, "Officer updated.")
        return redirect('officer_list')
    return render(request, 'assets/officer_form.html', {'officer': officer, 'title': 'Edit Officer'})


@require_fixed_assets_feature
def depreciation_method_list(request):
    """List all depreciation methods"""
    methods = DepreciationMethod.objects.all()
    return render(request, 'assets/depreciation_method_list.html', {'methods': methods})


@require_fixed_assets_feature
def depreciation_method_create(request):
    """Create new depreciation method"""
    if request.method == "POST":
        method = request.POST.get('method')
        if method:
            DepreciationMethod.objects.create(method=method)
            messages.success(request, f"Depreciation Method '{method}' created.")
            return redirect('depreciation_method_list')
    return render(request, 'assets/depreciation_method_form.html', {'title': 'Create Depreciation Method'})


@require_fixed_assets_feature
def depreciation_method_edit(request, uuid):
    """Edit depreciation method"""
    dep_method = get_object_or_404(DepreciationMethod, uuid=uuid)
    if request.method == "POST":
        dep_method.method = request.POST.get('method')
        dep_method.save()
        messages.success(request, "Depreciation Method updated.")
        return redirect('depreciation_method_list')
    return render(request, 'assets/depreciation_method_form.html', {'dep_method': dep_method, 'title': 'Edit Depreciation Method'})

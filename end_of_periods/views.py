from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.db.models import Sum
from transactions.models import Memtrans, InterestRate
from transactions.utils import generate_int_cal
from datetime import datetime

def calculate_interest(request):
    results = []
    total_amount_sum = 0
    total_interest_sum = 0

    if request.method == 'POST':
        gl_no = request.POST.get('gl_no')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        action = request.POST.get('action')

        try:
            interest_rate = InterestRate.objects.get(gl_no=gl_no)
        except InterestRate.DoesNotExist:
            return render(request, 'end_of_periods/calculate_interest.html', {
                'error': 'GL Number not found'
            })

        transactions = Memtrans.objects.filter(
            gl_no=gl_no,
            ses_date__range=[start_date, end_date],
            error='A'  # Exclude transactions where error is 'H'
        )

        # Aggregate by gl_no and ac_no
        aggregated_data = transactions.values('gl_no', 'ac_no').annotate(
            total_amount=Sum('amount')
        )

        results = []
        for data in aggregated_data:
            total_amount = data['total_amount']
            total_interest = (total_amount * interest_rate.rate) / 100

            results.append({
                'gl_no': data['gl_no'],
                'ac_no': data['ac_no'],
                'total_amount': total_amount,
                'interest_rate': interest_rate.rate,
                'total_interest': total_interest
            })

            total_amount_sum += total_amount
            total_interest_sum += total_interest
            trx_no_cal = generate_int_cal()

        if action == 'save':
            # Insert individual records for each result
            for result in results:
                Memtrans.objects.create(
                    branch=request.user.branch,  # Adjust if needed
                    customer=None,  # Adjust if needed
                    loans=None,  # Adjust if needed
                    cycle=None,  # Adjust if needed
                    gl_no=result['gl_no'],
                    ac_no=result['ac_no'],
                    trx_no=trx_no_cal,
                    ses_date=datetime.now().date(),  # Assuming today's date
                    app_date=datetime.now().date(),
                    amount=result['total_interest'],  # Save total interest instead of total amount
                    description='Interest Calculation',
                    error='A',
                    type='N',
                    code='MSI',
                    user=request.user
                )

            # Insert a summary record with summed total interest
            Memtrans.objects.create(
                branch=request.user.branch,  # Adjust if needed
                customer=None,  # Adjust if needed
                loans=None,  # Adjust if needed
                cycle=None,  # Adjust if needed
                gl_no=interest_rate.glno_debit_account,  # Debit GL Number from InterestRate
                ac_no=interest_rate.acno_debit_account,  # Debit Account Number from InterestRate
                trx_no=trx_no_cal,
                ses_date=datetime.now().date(),  # Assuming today's date
                app_date=datetime.now().date(),
                amount=-total_interest_sum,  # Save summed total interest
                description='Total Interest Calculation',
                error='A',
                type='N',
                code='MSI',
                user=request.user
                
            )

            return redirect('success')  # Redirect to a success page after saving

    return render(request, 'end_of_periods/calculate_interest.html', {
        'results': results,
        'total_amount_sum': total_amount_sum,
        'total_interest_sum': total_interest_sum
    })




def success(request):
    return render(request, 'end_of_periods/success.html')



def end_of_periods(request):
   
    return render(request, 'end_of_periods/end_of_periods.html')
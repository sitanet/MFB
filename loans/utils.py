from datetime import timedelta


def calculate_loan_schedule(loan_amount, interest_rate, payment_freq, num_install, appli_date):
    loan_amount = float(loan_amount)
    interest_rate = float(interest_rate)
    payment_freq = int(payment_freq)
    num_install = int(num_install)

    # Assuming simple interest for demonstration
    monthly_interest_rate = interest_rate / 100 / 12
    total_payment = loan_amount * monthly_interest_rate / (1 - (1 + monthly_interest_rate) ** -num_install)

    # Calculate loan schedule
    loan_schedule = []
    current_date = appli_date
    for i in range(num_install):
        interest_payment = loan_amount * monthly_interest_rate
        principal_payment = total_payment - interest_payment

        loan_schedule.append({
            'installment': i + 1,
            'payment_date': current_date,
            'principal_payment': principal_payment,
            'interest_payment': interest_payment,
            'total_payment': total_payment,
            'principal_remaining': loan_amount - principal_payment,
        })

        # Update current date for the next installment
        current_date += timedelta(days=30)  # Assuming monthly payments for demonstration

        # Update the remaining loan amount for the next iteration
        loan_amount -= principal_payment

    return loan_schedule

def calculate_straight_line_interest_schedule(loan_amount, interest_rate, num_install, appli_date, interest_calculation_method):
    loan_amount = float(loan_amount)
    interest_rate = float(interest_rate)
    num_install = int(num_install)

    # Assuming straight-line compound interest for demonstration
    monthly_interest_rate = interest_rate / 100 / 12
    total_payment = loan_amount * (1 + monthly_interest_rate * num_install) / num_install

    # Calculate loan schedule
    loan_schedule = []
    current_date = appli_date
    remaining_loan_amount = loan_amount

    for i in range(num_install):
        interest_payment = remaining_loan_amount * monthly_interest_rate

        if interest_calculation_method == 'straight_line':
            interest_payment = (loan_amount / num_install) * (1 + monthly_interest_rate * (num_install - i - 1))

        principal_payment = total_payment - interest_payment

        loan_schedule.append({
            'installment': i + 1,
            'payment_date': current_date,
            'principal_payment': principal_payment,
            'interest_payment': interest_payment,
            'total_payment': total_payment,
            'principal_remaining': remaining_loan_amount - principal_payment,
        })

        # Update current date for the next installment
        current_date += timedelta(days=30)  # Assuming monthly payments for demonstration

        # Update the remaining loan amount for the next iteration
        remaining_loan_amount -= principal_payment

    return loan_schedule






from datetime import timedelta

def calculate_due_date(disbursement_date, payment_freq, num_install):
    if payment_freq == 'daily':
        due_date = disbursement_date + timedelta(days=num_install)
    elif payment_freq == 'weekly':
        due_date = disbursement_date + timedelta(weeks=num_install)
    elif payment_freq == 'biweekly':
        due_date = disbursement_date + timedelta(weeks=2 * num_install)
    elif payment_freq == 'monthly':
        due_date = add_months(disbursement_date, num_install)
    elif payment_freq == 'quarterly':
        due_date = add_months(disbursement_date, 3 * num_install)
    elif payment_freq == 'yearly':
        due_date = add_months(disbursement_date, 12 * num_install)
    else:
        due_date = None
    return due_date

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, [31, 29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return sourcedate.replace(year=year, month=month, day=day)

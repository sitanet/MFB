import random
import string

def generate_withdrawal_id():
    digits = ''.join(random.choice(string.digits) for _ in range(7))
    alphabet = 'W'
    return digits + alphabet


def generate_deposit_id():
    digits = ''.join(random.choice(string.digits) for _ in range(7))
    alphabet = 'D'
    return digits + alphabet


def generate_income_id():
    digits = ''.join(random.choice(string.digits) for _ in range(7))
    alphabet = 'I'
    return digits + alphabet

def generate_expense_id():
    digits = ''.join(random.choice(string.digits) for _ in range(7))
    alphabet = 'E'
    return digits + alphabet


def generate_general_journal_id():
    digits = ''.join(random.choice(string.digits) for _ in range(7))
    alphabet = 'G'
    return digits + alphabet


def generate_loan_disbursement_id():
    digits = ''.join(random.choice(string.digits) for _ in range(6))
    alphabet = 'LD'
    return digits + alphabet

def generate_loan_repayment_id():
    digits = ''.join(random.choice(string.digits) for _ in range(6))
    alphabet = 'LP'
    return digits + alphabet

def generate_loan_written_off_id():
    digits = ''.join(random.choice(string.digits) for _ in range(6))
    alphabet = 'LW'
    return digits + alphabet


def generate_int_cal():
    digits = ''.join(random.choice(string.digits) for _ in range(6))
    alphabet = 'I'
    return digits + alphabet

def generate_upload_excel():
    digits = ''.join(random.choice(string.digits) for _ in range(6))
    alphabet = 'U'
    return digits + alphabet
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Branch
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# Default Chart of Accounts data - inserted when a new branch is created
DEFAULT_CHART_OF_ACCOUNTS = [
    {'gl_no': '10000', 'gl_name': 'ASEETS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10100', 'gl_name': 'CASH', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10110', 'gl_name': 'VAULT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10111', 'gl_name': 'CASH IN VAULT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10101', 'gl_name': 'CASHIER TELLER 1', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10102', 'gl_name': 'CASHIER TELLER 2', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10103', 'gl_name': 'CASHIER TELLER 3', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10112', 'gl_name': 'CASH WITH LOAN OFFICERS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10113', 'gl_name': 'CASH IN TRANSIT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10114', 'gl_name': 'PETTY CASH/IMPREST', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10200', 'gl_name': 'BANK BALANCES & INVESTMENT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10201', 'gl_name': 'CURRENT ACCOUNT - COMMERCIAL BANK', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10202', 'gl_name': 'SAVINGS ACCOUNT - COMMERCIAL BANK', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10203', 'gl_name': 'DOMICILIARY ACCOUNT - USD', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10204', 'gl_name': 'DOMICILIARY ACCOUNT - EUR', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10205', 'gl_name': 'CBN SETTLEMENT ACCOUNT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10206', 'gl_name': 'TREASURY BILLS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10207', 'gl_name': 'GOVERNMENT BONDS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10208', 'gl_name': 'FIXED DEPOSIT INVESTMENTS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10209', 'gl_name': 'OTHER SHORT-TERM INVESTMENTS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10300', 'gl_name': 'OTHER RECEIVABLE & PREPAYMENTS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10301', 'gl_name': 'ACCOUNTS RECEIVABLES', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10302', 'gl_name': 'INTEREST RECEIVABLES INVESTMENT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10303', 'gl_name': 'STAFF LOAN RECEIVABLE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10304', 'gl_name': 'STAFF SALARY ADVANCE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10305', 'gl_name': 'PREPAID RENT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10306', 'gl_name': 'PREPAID INSURANCE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10307', 'gl_name': 'OTHER PREPAYMENTS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10400', 'gl_name': 'LOANS & ADVANCES', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10410', 'gl_name': 'LOAN PORTFOLIO', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10411', 'gl_name': 'INDIVIDUAL LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10412', 'gl_name': 'GROUP LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10413', 'gl_name': 'SME/MSME LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10414', 'gl_name': 'AGRICULTURAL LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10415', 'gl_name': 'SALARY ADVANCE LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10416', 'gl_name': 'COMSUMER LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10417', 'gl_name': 'ASSET/EQUIPMENT FURNITURE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10420', 'gl_name': 'LOAN CLASSIFICATION', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10421', 'gl_name': 'PERFORMING LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10422', 'gl_name': 'SUBSTANDARD LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10423', 'gl_name': 'DOUBTFUL LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10424', 'gl_name': 'LOST LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10430', 'gl_name': 'LOAN INTEREST & FEE RECEIVABLE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10431', 'gl_name': 'INTEREST RECEIVABLE ON LOANS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10432', 'gl_name': 'MANAGEMENT/PROCESSING, FEE RECEIVABLE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10440', 'gl_name': 'LOANS LOSS PROVISIONS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10441', 'gl_name': 'GENERAL LOAN LOSS PROVISION ', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10442', 'gl_name': 'SPECIFIC LOAN LOSS PROVISION', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10500', 'gl_name': 'PROPERTY, PLANT & EQUIPMENT(PPE)', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10510', 'gl_name': 'FIXED ASSETS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10511', 'gl_name': 'LAND', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10512', 'gl_name': 'BUILDING', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10513', 'gl_name': 'FURNITURE & FITTINGS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10514', 'gl_name': 'COMPUTERS & IT EQUIPMENT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10515', 'gl_name': 'MOTOR VEHICLE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10516', 'gl_name': 'SECURITY EQUIPMENT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10520', 'gl_name': 'ACCUMULATED DEPRECIATION', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10521', 'gl_name': 'ACCUMULATED DEPRECIATION BUILDING', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10522', 'gl_name': 'ACCUMULATED DEPRECIATION FURNITURE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10523', 'gl_name': 'ACCUMULATED DEPRECIATION COMPUTER', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10524', 'gl_name': 'ACCUMULATED DEPRECIATION VEHICLE', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10600', 'gl_name': 'OTHER ASSETS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10601', 'gl_name': 'INTANGIBLE ASSETS', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10602', 'gl_name': 'DEFERRED TAX ASSET', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '10603', 'gl_name': 'SUSPENSE ACCOUNT', 'account_type': 'ASSETS', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20000', 'gl_name': 'LIABILITIES', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20100', 'gl_name': 'DEMAND DEPOSIT', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20101', 'gl_name': 'CURRENT ACCOUNT', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20102', 'gl_name': 'STAFF CURRENT ACCOUNT', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20200', 'gl_name': 'VOLUNTARY SAVINGS', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20201', 'gl_name': 'SAVINGS ACCOUNT', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20202', 'gl_name': 'STAFF SAVINGS ACCOUNT', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20300', 'gl_name': 'FIXED/TERM DEPOSIT', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20301', 'gl_name': 'INDIVIDUAL', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20302', 'gl_name': 'CORPORATE', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20303', 'gl_name': 'STAFF', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20304', 'gl_name': 'ACCRUED INTEREST ON FIXED DEPOSIT', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20400', 'gl_name': 'BORROWING', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20401', 'gl_name': 'COMMERCIAL BANK LOANS', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20402', 'gl_name': 'CBN INTERVENTION FACILITIES', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20403', 'gl_name': 'DEVELOPMENT FINANCE INSTITUTION (DFI) LOANS', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20404', 'gl_name': 'SHAREHOLDER/RELATED PARTY LOANS', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20405', 'gl_name': 'ACCRUED INTEREST ON BORROWING', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20500', 'gl_name': 'OTHER LIABILITIES', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20501', 'gl_name': 'ACCOUNTS PAYABLE', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20502', 'gl_name': 'ACCRUED EXPENSES', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20503', 'gl_name': 'STAFF SALARY PAYABLE', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20504', 'gl_name': 'PAYE PAYABLE', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20505', 'gl_name': 'VAT PAYABLE', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '20506', 'gl_name': 'WITHHOLDING TAX PAYABLE', 'account_type': 'LIABILITIES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '30000', 'gl_name': 'EQUITY', 'account_type': 'EQUITY', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '30100', 'gl_name': 'SHAREHOLDERS\' FUND', 'account_type': 'EQUITY', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '30101', 'gl_name': 'SHARE CAPITAL', 'account_type': 'EQUITY', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '30102', 'gl_name': 'SHARE PREMIUM', 'account_type': 'EQUITY', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '30103', 'gl_name': 'STATUTORY RESERVE', 'account_type': 'EQUITY', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '30104', 'gl_name': 'REGULATORY RISK RESERVE', 'account_type': 'EQUITY', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '30105', 'gl_name': 'RETAINED EARNINGS', 'account_type': 'EQUITY', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40000', 'gl_name': 'INCOME', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40100', 'gl_name': 'INTEREST INCOME', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40101', 'gl_name': 'INTEREST ON LOANS - INDIVIDUAL', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40102', 'gl_name': 'INTEREST ON LOANS - GROUP', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40103', 'gl_name': 'INTEREST ON SME - LOANS', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40104', 'gl_name': 'INTEREST ON INVESTMENTS', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40200', 'gl_name': 'FEES & COMMISSION INCOME', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40201', 'gl_name': 'LOAN PROCESSING FEES', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40202', 'gl_name': 'ACCOUNT MAINTENANCE FEES', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40203', 'gl_name': 'PENALTY CHARGES', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40204', 'gl_name': 'SMS/E-CHANNEL FEES', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40300', 'gl_name': 'OTHER INCOME', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40301', 'gl_name': 'FOREIGN EXCHANGE GAIN', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40302', 'gl_name': 'GAIN ON ASSET DISPOSAL', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '40303', 'gl_name': 'MISCELLANEOUS INCOME', 'account_type': 'INCOME', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50000', 'gl_name': 'EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50100', 'gl_name': 'PERSONNEL EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50101', 'gl_name': 'STAFF SALARIES & WAGES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50102', 'gl_name': 'ALLOWANCES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50103', 'gl_name': 'PENSION CONTRIBUTION', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50104', 'gl_name': 'TRAINING & CAPACITY BUILDING', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50105', 'gl_name': 'STAFF WELFARE', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50200', 'gl_name': 'ADMINISTRATIVE EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50201', 'gl_name': 'RENT', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50202', 'gl_name': 'UTILITIES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50203', 'gl_name': 'OFFICE SUPPLIES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50204', 'gl_name': 'COMMUNICATION EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50205', 'gl_name': 'INSURANCE', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50206', 'gl_name': 'AUDIT & PROFESSIONAL FEES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50300', 'gl_name': 'OPERATING EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50301', 'gl_name': 'LOAN MONITORING EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50302', 'gl_name': 'FIELD OPERATIONS EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50303', 'gl_name': 'SECURITY EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50305', 'gl_name': 'REPAIRS & MAINTENANCE', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50400', 'gl_name': 'FINANCIAL EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50401', 'gl_name': 'INTEREST ON BORROWINGS', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50402', 'gl_name': 'BANK CHARGES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50403', 'gl_name': 'FOREIGN EXCHANGE LOSS', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50500', 'gl_name': 'IMPAIRMENT & PROVISIONS', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50501', 'gl_name': 'LOANS LOSS PROVISIONS EXPENSES', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
    {'gl_no': '50502', 'gl_name': 'ASSET IMPAIRMENT EXPENSE', 'account_type': 'EXPENSES', 'currency': 'NAGERIA', 'double_entry_type': 'DEBIT_CREDIT'},
]


def get_parent_gl_no(gl_no):
    """
    Determine the parent GL number based on hierarchy.
    Hierarchy logic:
    - 5 digit codes ending in non-zero at position 5 (e.g., 10111) -> parent is 4-digit pattern (10110)
    - 5 digit codes ending in 0 at position 5 (e.g., 10110) -> parent is 3-digit pattern (10100)
    - 4 digit codes ending in non-zero (e.g., 10101) -> parent is 3-digit pattern (10100)
    - 3 digit pattern codes (e.g., 10100) -> parent is 2-digit pattern (10000)
    - Top level codes (e.g., 10000) -> no parent
    """
    gl_no_str = str(gl_no).zfill(5)
    
    # Top level accounts (10000, 20000, etc.) have no parent
    if gl_no_str[1:] == '0000':
        return None
    
    # Find parent by zeroing out trailing digits
    # e.g., 10111 -> 10110 -> 10100 -> 10000
    for i in range(4, 0, -1):
        if gl_no_str[i] != '0':
            parent_gl = gl_no_str[:i] + '0' * (5 - i)
            return parent_gl
    
    return None


@receiver(post_save, sender=Branch)
def create_default_accounts(sender, instance, created, **kwargs):
    """Create default chart of accounts when a new branch is created"""
    if created:
        from accounts_admin.models import Account
        
        # Maps for converting string types to model constants
        account_type_map = {
            'ASSETS': Account.ASSETS,
            'LIABILITIES': Account.LIABILITIES,
            'EQUITY': Account.EQUITY,
            'EXPENSES': Account.EXPENSES,
            'INCOME': Account.INCOME,
        }
        
        currency_map = {
            'US_DOLLAR': Account.US_DOLLAR,
            'NAGERIA': Account.NAGERIA,
        }
        
        double_entry_map = {
            'DEBIT_CREDIT': Account.DEBIT_CREDIT,
            'CREDIT': Account.CREDIT,
            'DEBIT': Account.DEBIT,
        }
        
        # Dictionary to track created accounts by gl_no for setting headers
        created_accounts = {}
        
        # First pass: create all accounts without headers
        for acc_data in DEFAULT_CHART_OF_ACCOUNTS:
            account = Account.all_objects.create(
                branch=instance,
                gl_no=acc_data['gl_no'],
                gl_name=acc_data['gl_name'],
                account_type=account_type_map.get(acc_data['account_type'], Account.ASSETS),
                currency=currency_map.get(acc_data['currency'], Account.NAGERIA),
                double_entry_type=double_entry_map.get(acc_data['double_entry_type'], Account.DEBIT_CREDIT),
            )
            created_accounts[acc_data['gl_no']] = account
        
        # Second pass: set headers based on GL number hierarchy
        for gl_no, account in created_accounts.items():
            parent_gl_no = get_parent_gl_no(gl_no)
            if parent_gl_no and parent_gl_no in created_accounts:
                account.header = created_accounts[parent_gl_no]
                account.save()


# ==================== AUTO LOAN REPAYMENT ON SESSION CLOSE ====================

@receiver(pre_save, sender=Branch)
def track_session_status_change(sender, instance, **kwargs):
    """Track if session_status is changing from Open to Closed"""
    if instance.pk:
        try:
            old_instance = Branch.objects.get(pk=instance.pk)
            instance._old_session_status = old_instance.session_status
        except Branch.DoesNotExist:
            instance._old_session_status = None
    else:
        instance._old_session_status = None


@receiver(post_save, sender=Branch)
def process_auto_loan_repayments_on_session_close(sender, instance, created, **kwargs):
    """
    Previously processed automatic loan repayments when session is closed.
    Now disabled - repayments are processed via modal review in session_mgt view.
    """
    # Auto-processing disabled - now handled via modal review before session close
    pass


def process_auto_loan_repayments(branch):
    """
    Process automatic loan repayments for all enabled loan GL accounts.
    Debits customer savings account (starting with 2) and credits loan account.
    """
    from django.db import transaction
    from django.db.models import Sum
    from accounts_admin.models import Account, LoanAutoRepaymentSetting
    from loans.models import Loans, LoanHist
    from transactions.models import Memtrans
    from transactions.utils import generate_loan_repayment_id
    
    session_date = branch.session_date
    if not session_date:
        logger.warning(f"Branch {branch.branch_name} has no session date set")
        return
    
    # Get all enabled auto repayment settings for this branch's company
    company_branches = Branch.objects.filter(company=branch.company)
    branch_ids = list(company_branches.values_list('id', flat=True))
    
    enabled_settings = LoanAutoRepaymentSetting.all_objects.filter(
        branch_id__in=branch_ids,
        is_auto_repayment_enabled=True
    ).select_related('account')
    
    if not enabled_settings.exists():
        logger.info(f"No auto repayment settings enabled for branch {branch.branch_name}")
        return
    
    # Build a map of GL number to setting (for interest_income_gl_no)
    gl_to_setting = {setting.account.gl_no: setting for setting in enabled_settings}
    enabled_gl_numbers = list(gl_to_setting.keys())
    logger.info(f"Processing auto repayments for GL numbers: {enabled_gl_numbers}")
    
    # Get all active loans with enabled GL numbers that have outstanding balance
    loans = Loans.all_objects.filter(
        branch_id__in=branch_ids,
        gl_no__in=enabled_gl_numbers,
        disb_status='T',
        total_loan__gt=0
    ).select_related('customer')
    
    processed_count = 0
    skipped_count = 0
    
    for loan in loans:
        try:
            with transaction.atomic():
                # Get the setting for this loan's GL to access interest_income_gl_no
                setting = gl_to_setting.get(loan.gl_no)
                result = process_single_loan_repayment(loan, branch, session_date, setting)
                if result:
                    processed_count += 1
                else:
                    skipped_count += 1
        except Exception as e:
            logger.error(f"Error processing loan {loan.gl_no}-{loan.ac_no}: {str(e)}")
            skipped_count += 1
    
    logger.info(f"Auto loan repayment completed: {processed_count} processed, {skipped_count} skipped")


def process_single_loan_repayment(loan, branch, session_date, setting=None):
    """
    Process repayment for a single loan.
    Returns True if processed, False if skipped.
    
    Args:
        loan: The loan object to process
        branch: The branch object
        session_date: The session date
        setting: LoanAutoRepaymentSetting object containing interest_income_gl_no
    """
    from django.db.models import Sum
    from accounts_admin.models import Account
    from loans.models import LoanHist
    from transactions.models import Memtrans
    from transactions.utils import generate_loan_repayment_id
    
    customer = loan.customer
    if not customer:
        logger.warning(f"Loan {loan.gl_no}-{loan.ac_no} has no customer")
        return False
    
    # Check if interest income GL is configured in the setting
    if not setting or not setting.interest_income_gl_no:
        logger.warning(f"Loan {loan.gl_no}-{loan.ac_no} has no interest income GL configured in auto repayment settings")
        return False
    
    # Get the loan account settings
    try:
        account = Account.all_objects.get(gl_no=loan.gl_no, branch=loan.branch)
    except Account.DoesNotExist:
        logger.warning(f"Account not found for GL {loan.gl_no}")
        return False
    
    # Calculate outstanding principal and interest due up to session date
    disbursement_date = loan.disbursement_date
    if not disbursement_date:
        logger.warning(f"Loan {loan.gl_no}-{loan.ac_no} has no disbursement date")
        return False
    
    # Get total due from LoanHist (scheduled repayments) - filtered by branch for multi-tenancy
    outstanding_principal = LoanHist.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle,
        trx_date__gte=disbursement_date,
        trx_date__lte=session_date,
        trx_type='LD'  # Loan Due entries
    ).aggregate(total=Sum('principal'))['total'] or Decimal('0.00')
    
    outstanding_interest = LoanHist.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle,
        trx_date__gte=disbursement_date,
        trx_date__lte=session_date,
        trx_type='LD'
    ).aggregate(total=Sum('interest'))['total'] or Decimal('0.00')
    
    # Subtract already paid amounts (LP entries) - filtered by branch for multi-tenancy
    paid_principal = LoanHist.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle,
        trx_type='LP'  # Loan Payment entries (negative values)
    ).aggregate(total=Sum('principal'))['total'] or Decimal('0.00')
    
    paid_interest = LoanHist.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle,
        trx_type='LP'
    ).aggregate(total=Sum('interest'))['total'] or Decimal('0.00')
    
    # Calculate net due (LP entries are negative so we add them)
    net_principal_due = outstanding_principal + paid_principal
    net_interest_due = outstanding_interest + paid_interest
    
    if net_principal_due <= 0 and net_interest_due <= 0:
        logger.info(f"Loan {loan.gl_no}-{loan.ac_no} has no outstanding dues")
        return False
    
    # Get customer's savings account balance - filtered by branch for multi-tenancy
    customer_balance = Memtrans.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.cust_gl_no,
        ac_no=customer.ac_no,
        error='A'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_due = net_principal_due + net_interest_due
    
    if customer_balance <= 0:
        logger.info(f"Customer {customer.ac_no} has insufficient balance ({customer_balance}) for loan repayment")
        return False
    
    # Determine how much can be paid (up to available balance)
    amount_to_pay = min(customer_balance, total_due)
    
    if amount_to_pay <= 0:
        return False
    
    # Proportionally split between principal and interest
    if total_due > 0:
        principal_ratio = net_principal_due / total_due if total_due > 0 else Decimal('0')
        principal_to_pay = (amount_to_pay * principal_ratio).quantize(Decimal('0.01'))
        interest_to_pay = amount_to_pay - principal_to_pay
    else:
        principal_to_pay = Decimal('0.00')
        interest_to_pay = Decimal('0.00')
    
    # Generate unique transaction ID
    unique_id = generate_loan_repayment_id()
    
    # Create transactions
    # 1. Debit customer savings account (principal)
    Memtrans.all_objects.create(
        branch=branch,
        cust_branch=loan.branch,
        gl_no=loan.cust_gl_no,
        ac_no=customer.ac_no,
        cycle=loan.cycle,
        amount=-principal_to_pay,
        description=f'Auto Loan Repayment Principal - {customer.first_name} {customer.last_name}',
        error='A',
        type='C',
        account_type='S',
        ses_date=session_date,
        app_date=session_date,
        trx_no=unique_id,
        code='ALP',
        trx_type='AUTO_LP'
    )
    
    # 2. Credit loan account (principal)
    Memtrans.all_objects.create(
        branch=branch,
        cust_branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle,
        amount=principal_to_pay,
        description=f'Auto Loan Repayment Principal - {customer.first_name} {customer.last_name}',
        error='A',
        type='D',
        account_type='L',
        ses_date=session_date,
        app_date=session_date,
        trx_no=unique_id,
        code='ALP',
        trx_type='AUTO_LP'
    )
    
    # 3. Debit customer savings account (interest)
    if interest_to_pay > 0:
        Memtrans.all_objects.create(
            branch=branch,
            cust_branch=loan.branch,
            gl_no=loan.cust_gl_no,
            ac_no=customer.ac_no,
            cycle=loan.cycle,
            amount=-interest_to_pay,
            description=f'Auto Loan Repayment Interest - {customer.first_name} {customer.last_name}',
            error='A',
            type='C',
            account_type='S',
            ses_date=session_date,
            app_date=session_date,
            trx_no=unique_id,
            code='ALI',
            trx_type='AUTO_LP'
        )
        
        # 4. Credit interest income account (using interest_income_gl_no from setting)
        Memtrans.all_objects.create(
            branch=branch,
            cust_branch=loan.branch,
            gl_no=setting.interest_income_gl_no,
            ac_no='00000',  # Default account number for income GL
            cycle=loan.cycle,
            amount=interest_to_pay,
            description=f'Auto Loan Repayment Interest - {customer.first_name} {customer.last_name}',
            error='A',
            type='D',
            account_type='I',
            ses_date=session_date,
            app_date=session_date,
            trx_no=unique_id,
            code='ALI',
            trx_type='AUTO_LP'
        )
        
        # 5. Interest Accounting Adjustment (reduce balance sheet)
        # Debit Interest Receivable (reduce asset) and Credit Unearned Interest Income (reduce liability)
        if setting.int_receivable_gl_no and setting.unearned_int_income_gl_no:
            # Debit Interest Receivable GL (reduce the asset)
            Memtrans.all_objects.create(
                branch=branch,
                cust_branch=loan.branch,
                gl_no=setting.int_receivable_gl_no,
                ac_no='00000',
                cycle=loan.cycle,
                amount=-interest_to_pay,
                description=f'Auto Loan Interest Accounting - {customer.first_name} {customer.last_name}',
                error='A',
                type='D',
                account_type='I',
                ses_date=session_date,
                app_date=session_date,
                trx_no=unique_id,
                code='ALI',
                trx_type='AUTO_LP'
            )
            
            # Credit Unearned Interest Income GL (reduce the liability)
            Memtrans.all_objects.create(
                branch=branch,
                cust_branch=loan.branch,
                gl_no=setting.unearned_int_income_gl_no,
                ac_no='00000',
                cycle=loan.cycle,
                amount=interest_to_pay,
                description=f'Auto Loan Interest Accounting - {customer.first_name} {customer.last_name}',
                error='A',
                type='C',
                account_type='I',
                ses_date=session_date,
                app_date=session_date,
                trx_no=unique_id,
                code='ALI',
                trx_type='AUTO_LP'
            )
    
    # 6. Create LoanHist entry - filtered by branch for multi-tenancy
    lp_count = LoanHist.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle,
        trx_type='LP'
    ).count()
    
    LoanHist.all_objects.create(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle,
        period=lp_count + 1,
        trx_date=session_date,
        trx_type='LP',
        trx_naration='Auto Loan Repayment',
        principal=-principal_to_pay,
        interest=-interest_to_pay,
        penalty=Decimal('0.00'),
        trx_no=unique_id
    )
    
    # 7. Update loan totals - filtered by branch for multi-tenancy
    total_interest = LoanHist.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle
    ).aggregate(total=Sum('interest'))['total'] or Decimal('0.00')
    
    total_principal = LoanHist.all_objects.filter(
        branch=loan.branch,
        gl_no=loan.gl_no,
        ac_no=loan.ac_no,
        cycle=loan.cycle
    ).aggregate(total=Sum('principal'))['total'] or Decimal('0.00')
    
    loan.total_loan = total_principal + total_interest
    loan.total_interest = total_interest
    loan.save()
    
    logger.info(f"Auto repayment processed for loan {loan.gl_no}-{loan.ac_no}: Principal={principal_to_pay}, Interest={interest_to_pay}")
    return True

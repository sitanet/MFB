import uuid
from decimal import Decimal
from django.db.models import Sum

from customers.models import Customer
from transactions.models import Memtrans


def _normalize_account_part(part: str, width: int = 5) -> str:
    """
    Normalize GL or AC number to fixed width (default 5), zero-padded.
    Example: '123' → '00123'
    """
    if not part:
        return "0" * width
    return str(part).strip().zfill(width)[-width:]


def normalize_account(gl_no, ac_no):
    """
    Public normalizer used by views/serializers.
    Ensures both GL and AC are 5-digit, zero-padded strings.
    """
    return _normalize_account_part(gl_no), _normalize_account_part(ac_no)


def _user_customer(obj):
    """
    Return the Customer linked to the authenticated user (supports passing either
    a request or a user), or None if not found.
    """
    user = getattr(obj, "user", None) or obj
    if not user:
        return None
    is_auth = getattr(user, "is_authenticated", True)
    if not is_auth:
        return None
    return Customer.objects.filter(user=user).first()


def _owns_source_account(owner, gl_no: str, ac_no: str) -> bool:
    """
    Verify the (gl_no, ac_no) belongs to the given owner.
    'owner' can be a Customer instance, a request, or a user.
    """
    cust = owner if isinstance(owner, Customer) else _user_customer(owner)
    if not cust:
        return False

    input_gl = _normalize_account_part(gl_no)
    input_ac = _normalize_account_part(ac_no)

    db_gl = _normalize_account_part(getattr(cust, 'gl_no', ''))
    db_ac = _normalize_account_part(getattr(cust, 'ac_no', ''))

    return input_gl == db_gl and input_ac == db_ac


def _balance(gl_no: str, ac_no: str) -> Decimal:
    """
    Returns current balance for the given (gl_no, ac_no).
    Assumes Memtrans.amount is signed (CR positive, DR negative)
    so total balance = SUM(amount).
    """
    normalized_gl = _normalize_account_part(gl_no)
    normalized_ac = _normalize_account_part(ac_no)

    total = (
        Memtrans.objects.filter(gl_no=normalized_gl, ac_no=normalized_ac)
        .aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )
    return Decimal(total).quantize(Decimal("0.01"))


def _gen_trx_no(prefix="TRX", user_id=None) -> str:
    """
    Generate an uppercase transaction reference.
    If first arg is int, treat it as user_id and use default prefix TRX.
    """
    if isinstance(prefix, int):
        user_id = prefix
        prefix = "TRX"
    prefix = str(prefix or "TRX").upper()[:4]
    core = uuid.uuid4().hex[:8].upper()
    return f"{prefix}{core}"


def card_wallet_for_user(user):
    """
    Card wallet ledger mapping.
    Uses GL '20201' (savings) with user's id as a 5‑digit AC to isolate per-user card ledger.
    If you prefer a dedicated GL (e.g., '29000'), change it here.
    """
    return "20201", str(user.id).zfill(5)





# Add these functions to your existing api/helpers.py file

def normalize_phone(phone):
    """Normalize phone number to Nigerian format"""
    if not phone:
        return None
    
    # Remove all non-digits
    phone = ''.join(filter(str.isdigit, str(phone)))
    
    # Convert to Nigerian format (234...)
    if phone.startswith('234'):
        return phone
    elif phone.startswith('0'):
        return '234' + phone[1:]
    elif len(phone) == 10:
        return '234' + phone
    else:
        return phone


def parse_account_number(account_number):
    """Parse account number into GL and AC components"""
    if not account_number:
        raise ValueError("Account number is required")
    
    # Remove any non-digits
    digits = ''.join(filter(str.isdigit, account_number))
    
    if len(digits) < 10:
        raise ValueError("Account number must be at least 10 digits")
    
    if len(digits) >= 10:
        gl_no = digits[:5]
        ac_no = digits[5:]
        return gl_no, ac_no
    else:
        raise ValueError("Invalid account number format")


def safe_customer_lookup(gl_no, ac_no, **additional_filters):
    """Safely lookup customer with additional filters"""
    try:
        from customers.models import Customer
        filters = {
            'gl_no': str(gl_no),
            'ac_no': str(ac_no),
            **additional_filters
        }
        return Customer.objects.get(**filters)
    except:
        return None


def format_error_response(error_message, error_code=None):
    """Format error response consistently"""
    response = {'error': str(error_message)}
    if error_code:
        response['error_code'] = error_code
    return response


def format_success_response(data, message=None):
    """Format success response consistently"""
    response = {'success': True}
    if message:
        response['message'] = message
    if isinstance(data, dict):
        response.update(data)
    else:
        response['data'] = data
    return response
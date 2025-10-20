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


def _user_customer(request):
    """
    Return the Customer linked to the authenticated user, or None.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    return Customer.objects.filter(user=user).first()


def _owns_source_account(customer: Customer, gl_no: str, ac_no: str) -> bool:
    """
    Verify the source account belongs to the given customer.
    Normalizes both input and DB values to 5-digit zero-padded strings.
    """
    if not customer:
        return False

    input_gl = _normalize_account_part(gl_no)
    input_ac = _normalize_account_part(ac_no)

    db_gl = _normalize_account_part(getattr(customer, 'gl_no', ''))
    db_ac = _normalize_account_part(getattr(customer, 'ac_no', ''))

    return input_gl == db_gl and input_ac == db_ac


def _balance(gl_no: str, ac_no: str) -> Decimal:
    """
    Returns current balance for the given (gl_no, ac_no).
    Assumes Memtrans.amount is signed:
      - CR: positive
      - DR: negative
    So total balance = SUM(amount).
    """
    normalized_gl = _normalize_account_part(gl_no)
    normalized_ac = _normalize_account_part(ac_no)

    total = (
        Memtrans.objects.filter(
            gl_no=normalized_gl,
            ac_no=normalized_ac
        ).aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )
    return Decimal(total).quantize(Decimal("0.01"))


def _gen_trx_no(user_id: int) -> str:
    """
    Generate an 8-character uppercase alphanumeric transaction reference.
    Safe for varchar(20) fields.
    """
    return uuid.uuid4().hex[:8].upper()
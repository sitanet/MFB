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
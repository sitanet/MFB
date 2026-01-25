from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name='abs')
def absolute(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter
def number_format(value):
    """Formats a number with commas and brackets for negatives."""
    try:
        value = float(value)
        if value < 0:
            return f'({abs(value):,.2f})'
        return f'{value:,.2f}'
    except (ValueError, TypeError):
        return value


@register.filter
def currency(value):
    """Format value as currency with commas, always positive display"""
    try:
        value = float(value)
        return f'{abs(value):,.2f}'
    except (ValueError, TypeError):
        return '0.00'


@register.filter
def currency_signed(value):
    """Format value as currency with sign indicator"""
    try:
        value = float(value)
        if value < 0:
            return f'({abs(value):,.2f})'
        return f'{value:,.2f}'
    except (ValueError, TypeError):
        return '0.00'


@register.filter
def positive_only(value):
    """Return value only if positive, otherwise return 0"""
    try:
        value = float(value)
        return max(0, value)
    except (ValueError, TypeError):
        return 0


@register.filter
def debit_amount(value):
    """Return absolute value if negative (debit), otherwise 0"""
    try:
        value = float(value)
        if value < 0:
            return abs(value)
        return 0
    except (ValueError, TypeError):
        return 0


@register.filter
def credit_amount(value):
    """Return value if positive (credit), otherwise 0"""
    try:
        value = float(value)
        if value > 0:
            return value
        return 0
    except (ValueError, TypeError):
        return 0


@register.filter
def format_balance(value):
    """Format balance - show negative in brackets with red styling"""
    try:
        value = float(value)
        if value < 0:
            return f'<span class="text-danger">({abs(value):,.2f})</span>'
        elif value > 0:
            return f'<span class="text-success">{value:,.2f}</span>'
        else:
            return f'<span class="text-muted">0.00</span>'
    except (ValueError, TypeError):
        return '0.00'


@register.filter
def get_by_id(queryset, id):
    """Retrieve an object from a queryset by its ID."""
    return queryset.filter(id=id).first()


@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def add_values(value, arg):
    """Add arg to value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage of value from total"""
    try:
        total = float(total)
        if total == 0:
            return '0.00%'
        pct = (float(value) / total) * 100
        return f'{pct:.2f}%'
    except (ValueError, TypeError):
        return '0.00%'

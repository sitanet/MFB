from django import template

register = template.Library()

@register.filter(name='abs')
def absolute(value):
    return abs(value)



# custom_filters.py

from django import template

register = template.Library()

@register.filter
def number_format(value):
    """Formats a number with commas and brackets for negatives."""
    try:
        value = float(value)
        if value < 0:
            return f'({abs(value):,.2f})'
        return f'{value:,.2f}'
    except (ValueError, TypeError):
        return value  # Return as-is if not a valid number




from django import template

register = template.Library()

@register.filter
def get_by_id(queryset, id):
    """Retrieve an object from a queryset by its ID."""
    return queryset.filter(id=id).first()

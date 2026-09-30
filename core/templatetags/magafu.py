from decimal import Decimal, InvalidOperation

from django import template
from django.utils.http import urlencode

register = template.Library()

STATUS_CLASSES = {
    "PENDING": "st-wait",
    "APPROVED": "st-info",
    "ACTIVE": "st-active",
    "COMPLETED": "st-done",
    "REJECTED": "st-muted",
    "WRITTEN_OFF": "st-muted",
    "OVERDUE": "st-late",
    "SENT": "st-done",
    "FAILED": "st-late",
    "SKIPPED": "st-muted",
}


@register.filter
def money(value):
    try:
        return f"{Decimal(value or 0):,.0f}"
    except (InvalidOperation, TypeError, ValueError):
        return value


@register.filter
def status_class(value):
    return STATUS_CLASSES.get(value, "st-muted")


@register.simple_tag(takes_context=True)
def query_with(context, **kwargs):
    """Inabadilisha parameter moja kwenye URL huku ikibakiza nyingine (kwa pagination/filters)."""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return "?" + urlencode(params, doseq=True)

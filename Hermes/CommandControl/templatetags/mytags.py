
from django import template

register = template.Library()

@register.filter
def ashex(value):
    return hex(value)
from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split a string by the given delimiter"""
    if not value:
        return []
    return value.split(arg)

@register.filter
def strip(value):
    """Strip whitespace from a string"""
    if not value:
        return ''
    return value.strip()
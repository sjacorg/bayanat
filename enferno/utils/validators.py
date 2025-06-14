import re


def validate_required(value):
    if value is None or value == "":
        return "This field is required."
    return None


def validate_min_length(value, min_length):
    if value is not None and len(value) < min_length:
        return f"Minimum length is {min_length}."
    return None


def validate_max_length(value, max_length):
    if value is not None and len(value) > max_length:
        return f"Maximum length is {max_length}."
    return None


def validate_pattern(value, pattern):
    if value is not None and not re.match(pattern, value):
        return "Value does not match the required pattern."
    return None


def validate_min(value, min_val):
    if value is not None and value < min_val:
        return f"Minimum value is {min_val}."
    return None


def validate_max(value, max_val):
    if value is not None and value > max_val:
        return f"Maximum value is {max_val}."
    return None

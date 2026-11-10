from decimal import Decimal, InvalidOperation

def parse_difficulty(value):
    try:
        if isinstance(value, bool):
            raise ValueError()
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('difficulty must be a number from 1 to 10.') from None
    if not result.is_finite() or not Decimal(1) <= result <= Decimal(10):
        raise ValueError('difficulty must be a number from 1 to 10.')
    return result

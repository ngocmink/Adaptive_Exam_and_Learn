from flask import request
from werkzeug.exceptions import BadRequest

from app.common.responses import success_response
from app.extensions import db


DEFAULT_LIMIT = 9
MAX_LIMIT = 100


def positive_int(name, default=None, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise BadRequest(f"{name} must be a positive integer.") from None
    if value < 1 or (maximum is not None and value > maximum):
        if maximum is not None:
            raise BadRequest(f"{name} must be between 1 and {maximum}.")
        raise BadRequest(f"{name} must be positive.")
    return value


def boolean_arg(name, default=False):
    raw = request.args.get(name)
    if raw is None:
        return default
    if raw.lower() in ("true", "1"):
        return True
    if raw.lower() in ("false", "0"):
        return False
    raise BadRequest(f"{name} must be true or false.")


def get_page_args():
    return (
        positive_int("page", 1),
        positive_int("limit", DEFAULT_LIMIT, MAX_LIMIT),
    )


def pagination_data(result):
    return {
        "page": result.page,
        "limit": result.per_page,
        "total_records": result.total,
        "total_pages": result.pages,
    }


def paginate(statement, serialize, default_limit=DEFAULT_LIMIT):
    page = positive_int("page", 1)
    limit = positive_int("limit", default_limit, MAX_LIMIT)
    result = db.paginate(statement, page=page, per_page=limit, error_out=False)
    return success_response(
        [serialize(item) for item in result.items],
        pagination={
            "page": page,
            "limit": limit,
            "total_records": result.total,
            "total_pages": result.pages,
        },
    )

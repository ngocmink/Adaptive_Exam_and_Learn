from flask import request


DEFAULT_LIMIT = 9
MAX_LIMIT = 100


def get_page_args():
    """Read and validate page/limit query parameters."""
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
    except (TypeError, ValueError):
        raise ValueError("page và limit phải là số nguyên.") from None

    if page < 1:
        raise ValueError("page phải lớn hơn hoặc bằng 1.")
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit phải nằm trong khoảng 1 đến {MAX_LIMIT}.")

    return page, limit


def pagination_data(pagination):
    return {
        "page": pagination.page,
        "limit": pagination.per_page,
        "total_records": pagination.total,
        "total_pages": pagination.pages,
    }

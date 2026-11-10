from flask import request
from werkzeug.exceptions import BadRequest
from app.extensions import db
from app.common.responses import success_response

def positive_int(name, default=None, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise BadRequest(f'{name} must be a positive integer.')
    if value < 1 or (maximum is not None and value > maximum):
        raise BadRequest(f'{name} must be between 1 and {maximum}.' if maximum else f'{name} must be positive.')
    return value

def boolean_arg(name, default=False):
    raw = request.args.get(name)
    if raw is None:
        return default
    if raw.lower() in ('true', '1'):
        return True
    if raw.lower() in ('false', '0'):
        return False
    raise BadRequest(f'{name} must be true or false.')

def paginate(statement, serialize, default_limit=9):
    page = positive_int('page', 1)
    limit = positive_int('limit', default_limit, 100)
    result = db.paginate(statement, page=page, per_page=limit, error_out=False)
    return success_response([serialize(item) for item in result.items], pagination={
        'page': page, 'limit': limit, 'total_records': result.total, 'total_pages': result.pages,
    })

def get_page_args():
    return positive_int('page', 1), positive_int('limit', 9, 100)

def pagination_data(result):
    return {'page': result.page, 'limit': result.per_page,
            'total_records': result.total, 'total_pages': result.pages}

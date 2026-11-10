from flask import jsonify


def success_response(data=None, message="Thành công", pagination=None, status=200):
    body = {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
        "pagination": pagination,
    }

    return jsonify(body), status


def error_response(message="Có lỗi xảy ra", status=400, data=None):
    body = {
        "success": False,
        "message": message,
        "data": data if data is not None else {},
        "pagination": None,
    }

    return jsonify(body), status

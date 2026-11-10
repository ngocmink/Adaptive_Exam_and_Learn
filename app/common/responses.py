from flask import jsonify


def success_response(data=None, message="Thành công", pagination=None, status=200):
    return jsonify(
        success=True,
        message=message,
        data={} if data is None else data,
        pagination=pagination,
    ), status


def error_response(message="Có lỗi xảy ra", status=400, data=None):
    return jsonify(
        success=False,
        message=message,
        data={} if data is None else data,
        pagination=None,
    ), status

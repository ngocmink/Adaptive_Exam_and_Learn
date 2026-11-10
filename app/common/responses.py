from flask import jsonify

def success_response(data=None, message='Success', pagination=None, status=200):
    return jsonify(success=True, message=message, data=data, pagination=pagination), status

def error_response(message='Request failed.', status=400, data=None):
    return jsonify(success=False, message=message, data=data, pagination=None), status

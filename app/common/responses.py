from flask import jsonify

def success_response(data=None, message='Success', pagination=None, status=200):
    return jsonify(success=True, message=message, data=data, pagination=pagination), status

def error_response(message, status=400):
    return jsonify(success=False, message=message, data=None, pagination=None), status

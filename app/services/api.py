from flask import jsonify

def api_ok(**kwargs):
    return jsonify(success=True, **kwargs)

def api_error(message, **kwargs):
    return jsonify(success=False, error=message, **kwargs)

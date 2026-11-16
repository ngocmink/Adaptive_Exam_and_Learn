"""Server-only Supabase Storage API integration; never log keys or signed URLs."""
import json
import re
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from flask import current_app, make_response, url_for


class StorageError(Exception):
    def __init__(self, message='PDF storage is temporarily unavailable.', status=502):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a backend API key to another destination.


def private_response(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.vary.add('Cookie')
        return response
    return wrapped


def validate_storage_location(bucket, path):
    configured = current_app.config.get('SUPABASE_STORAGE_BUCKET', 'materials')
    if not isinstance(bucket, str) or bucket != configured or not re.fullmatch(r'[A-Za-z0-9_-]+', bucket):
        raise ValueError('Use the configured materials bucket.')
    if (not isinstance(path, str) or not path or len(path) > 1024
            or path.startswith('/') or '\\' in path
            or any(part in ('', '.', '..') for part in path.split('/'))
            or any(ord(char) < 32 or ord(char) == 127 for char in path)
            or not path.lower().endswith('.pdf')):
        raise ValueError('storage_path must be a relative PDF path inside the bucket.')
    return bucket, path


def _settings():
    base = (current_app.config.get('SUPABASE_URL') or '').rstrip('/')
    key = current_app.config.get('SUPABASE_SECRET_KEY') or ''
    parsed = urlsplit(base)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.path
            or parsed.query or parsed.fragment or parsed.username or parsed.password
            or not key.startswith('sb_secret_')):
        raise StorageError('PDF storage is not configured.', 503)
    return base, key


def storage_json(method, path, body=None):
    base, key = _settings()
    request = Request(base + '/storage/v1/' + path,
        data=json.dumps(body).encode('utf-8') if body is not None else None,
        headers={'apikey': key, 'Content-Type': 'application/json', 'Accept': 'application/json'},
        method=method)
    try:
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            return json.loads(response.read(65536))
    except HTTPError as error:
        # Read only enough to distinguish a missing object. Do not expose upstream bodies.
        try:
            details = json.loads(error.read(65536))
            missing = details.get('error') in ('not_found', 'Not Found') or details.get('statusCode') in (404, '404')
        except (ValueError, AttributeError):
            missing = False
        error.close()
        if error.code == 404 or missing:
            raise StorageError('PDF file was not found in storage.', 404) from None
        raise StorageError() from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise StorageError() from None


def create_pdf_url(bucket, path):
    validate_storage_location(bucket, path)
    base, _ = _settings()
    object_path = quote(bucket, safe='') + '/' + quote(path, safe='/')
    result = storage_json('POST', 'object/sign/' + object_path, {'expiresIn': 3600})
    if not isinstance(result, dict):
        raise StorageError()
    signed = result.get('signedURL', '')
    if not isinstance(signed, str):
        raise StorageError()
    # The REST API returns /object/sign/...; support a full same-origin URL too.
    if signed.startswith('/object/sign/'):
        signed = base + '/storage/v1' + signed
    elif signed.startswith('/storage/v1/object/sign/'):
        signed = base + signed
    expected = urlsplit(base)
    parsed = urlsplit(signed)
    if ((parsed.scheme, parsed.netloc) != (expected.scheme, expected.netloc)
            or parsed.path != '/storage/v1/object/sign/' + object_path
            or not parsed.query or parsed.fragment
            or any(ord(c) < 32 for c in signed)):
        raise StorageError()
    return signed


def legacy_pdf_url(value):
    """Normalize old pdf/... paths without exposing the whole project root."""
    parsed = urlsplit(value or '')
    if parsed.scheme in ('http', 'https') and parsed.netloc and not parsed.username and not parsed.password:
        return value
    path = parsed.path
    if path.startswith('/static/'):
        path = path[len('/static/'):]
    if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment
            or not path.startswith('pdf/') or '\\' in path
            or any(part in ('', '.', '..') for part in path.split('/'))):
        raise StorageError('This material does not have a supported PDF location.', 404)
    return url_for('static', filename=path)


def material_source(body, existing=None):
    """Validate an admin's complete source replacement, leaving other updates alone."""
    if existing is not None and not any(k in body for k in ('file_url','storage_bucket','storage_path')):
        return {}
    path = body.get('storage_path') or None
    bucket = body.get('storage_bucket') or None
    file_url = body.get('file_url') or None
    if path or bucket:
        bucket = bucket or current_app.config.get('SUPABASE_STORAGE_BUCKET', 'materials')
        validate_storage_location(bucket, path)
        if file_url:
            raise ValueError('Choose a storage path or a file URL, not both.')
        return {'storage_bucket': bucket, 'storage_path': path, 'file_url': None}
    if not isinstance(file_url, str) or not file_url.strip():
        raise ValueError('Provide a file_url or storage_path.')
    try:
        legacy_pdf_url(file_url.strip())
    except StorageError as error:
        raise ValueError(str(error)) from None
    return {'file_url': file_url.strip(), 'storage_bucket': None, 'storage_path': None}

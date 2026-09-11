import base64
import hashlib
import hmac
import json
import secrets
import time
from fastapi import HTTPException

ITERATIONS = 310000

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'

def verify_password(password, encoded):
    _, iterations, salt, expected = encoded.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(actual, expected)

def derive_device_key(device_token, device_id):
    return hmac.new(device_token.encode(), device_id.encode(), hashlib.sha256).hexdigest()

def key_hash(key):
    return hashlib.sha256(key.encode()).hexdigest()

def issue_token(username, role, secret, lifetime):
    payload = {'sub': username, 'role': role, 'exp': int(time.time()) + lifetime, 'nonce': secrets.token_hex(8)}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).rstrip(b'=').decode()
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + '.' + signature

def decode_token(token, secret):
    try:
        body, signature = token.split('.')
        expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError('signature')
        result = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
        if result['exp'] <= time.time() or result['role'] not in {'viewer', 'operator', 'admin'}:
            raise ValueError('expired or invalid role')
        return result
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise HTTPException(401, 'Invalid or expired session') from None

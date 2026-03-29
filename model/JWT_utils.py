import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from model.User import User

logger = logging.getLogger(__name__)

SECRET_KEY = "your-jwt-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRATION_HOURS = 24


def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning('Token expired')
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f'Invalid token: {str(e)}')
        return None


def get_current_user():
    token = None

    token = request.cookies.get('token')

    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    try:
        user = User.query.get(payload.get('user_id'))
        return user
    except Exception as e:
        logger.error(f'Error fetching user: {str(e)}')
        return None


def jwt_required():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()

            if not user:
                return jsonify({'error': 'Authentication required'}), 401

            from flask import g
            g.current_user = user

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def optional_auth():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g
            user = get_current_user()
            g.current_user = user

            return f(*args, **kwargs)
        return decorated_function
    return decorator

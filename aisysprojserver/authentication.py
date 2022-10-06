""" Functionality for password hashing and checking.

Design decisions:
* The way a password is stored is indicated by a prefix.
    That makes it possible to change the scheme later on if desired.
* We do not allow users to set a password (the server sets high-entropy passwords).
    That way we don't have to use slow hashing algorithms like bcrypt.
"""
import base64
import hashlib
import secrets

from flask import request
from werkzeug.exceptions import Unauthorized, BadRequest

from aisysprojserver import config


def _sha256hash(password: str) -> str:
    hashed_pwd = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return f'sha256:{hashed_pwd}'


default_pwd_hash = _sha256hash


def require_password_match(password: str, stored_hash: str):
    if stored_hash.startswith('sha256:'):
        if stored_hash != _sha256hash(password):
            raise Unauthorized(description='wrong password')
    else:
        raise Unauthorized(description='unknown hashing algorithm used for stored password')


def require_admin_auth():
    content = request.get_json()
    if content is not None and 'admin-pwd' in content:
        password = content['admin-pwd']
    elif 'Authorization' in request.headers:
        val = request.headers['Authorization'].split()
        if len(val) != 2:
            raise BadRequest(f'Bad value for Authorization header')
        elif val[0] != 'Basic':
            raise BadRequest(f'Bad authentication scheme in Authorization header')
        else:
            password = base64.decodebytes(val[1].encode()).decode()
    else:
        raise Unauthorized(description='admin authorization is required')
    if not isinstance(password, str):
        raise BadRequest('Bad value for "admin-pwd"')
    require_password_match(password, config.get().ADMIN_AUTH)


def generate_admin_password():
    password = secrets.token_urlsafe(32)
    hash_ = default_pwd_hash(password)
    print(f'Generated password: {password}')
    print(f'Associated hash (for server config): {hash_}')


if __name__ == '__main__':
    generate_admin_password()

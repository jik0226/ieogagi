# Test cases for security/semgrep/crypto-secrets.yml.
# Annotations: the line after a ruleid comment must be reported; after an ok comment it must stay silent.
import hashlib
import os
import secrets

import httpx
import requests

# ruleid: ieogagi-no-insecure-random
import random

# ruleid: ieogagi-no-insecure-random
import random as rnd

# ruleid: ieogagi-no-insecure-random
from random import choice

# ruleid: ieogagi-no-insecure-random
from random import randint as ri

# ok: ieogagi-no-insecure-random
token_value = secrets.token_urlsafe(32)


def hashes(data, password):
    # ruleid: ieogagi-no-weak-hash
    hashlib.md5(data)
    # ruleid: ieogagi-no-weak-hash
    hashlib.sha1(data)
    # ruleid: ieogagi-no-weak-hash
    hashlib.new("md5", data)
    # ruleid: ieogagi-no-weak-hash
    hashlib.new("SHA1", data)
    # ruleid: ieogagi-no-weak-hash
    hashlib.sha256(password.encode())
    # ruleid: ieogagi-no-weak-hash
    hashlib.sha512(password)
    # ruleid: ieogagi-no-weak-hash
    hashlib.new("sha256", password.encode())
    # ok: ieogagi-no-weak-hash
    hashlib.sha256(data)
    # ok: ieogagi-no-weak-hash
    hashlib.sha256(data).hexdigest()
    # ok: ieogagi-no-weak-hash
    hashlib.pbkdf2_hmac("sha256", password, data, 600000)


def secrets_assignments(settings):
    # ruleid: ieogagi-no-hardcoded-secret
    password = "hunter2"
    # ruleid: ieogagi-no-hardcoded-secret
    api_key = "abc123"
    # ruleid: ieogagi-no-hardcoded-secret
    SECRET_KEY = "change-me"
    # ruleid: ieogagi-no-hardcoded-secret
    settings.session_token = "abc"
    # ruleid: ieogagi-no-hardcoded-secret
    private_key: str = "-----BEGIN"
    # ruleid: ieogagi-no-hardcoded-secret
    connect(password="hunter2")
    # ruleid: ieogagi-no-hardcoded-secret
    SECRET_KEY = b"change-me"
    # ruleid: ieogagi-no-hardcoded-secret
    settings.session_secret = b"abc"
    # ruleid: ieogagi-no-hardcoded-secret
    api_token: bytes = b"abc"
    # ruleid: ieogagi-no-hardcoded-secret
    connect(secret=b"abc")
    # ruleid: ieogagi-no-hardcoded-secret
    PASSWORD = f"hunter2"
    # ruleid: ieogagi-no-hardcoded-secret
    settings.api_key = f"abc123"
    # ruleid: ieogagi-no-hardcoded-secret
    connect(password=f"hunter2")
    # ruleid: ieogagi-no-hardcoded-secret
    credentials = {"password": "hunter2"}
    # ruleid: ieogagi-no-hardcoded-secret
    headers = {"Content-Type": "json", "api_key": "abc123"}
    # ruleid: ieogagi-no-hardcoded-secret
    config = {"SECRET_KEY": b"abc"}
    # ruleid: ieogagi-no-hardcoded-secret
    config = {'private_key': '-----BEGIN'}
    # ruleid: ieogagi-no-hardcoded-secret
    mixed = {"password": "", "token": "abc"}
    # ruleid: ieogagi-no-hardcoded-secret
    multiline = {
        "user": "admin",
        "password": "hunter2",
    }
    # ok: ieogagi-no-hardcoded-secret
    password = ""
    # ok: ieogagi-no-hardcoded-secret
    secret_key = b""
    # ok: ieogagi-no-hardcoded-secret
    password = f""
    # ok: ieogagi-no-hardcoded-secret
    password = f"{settings.prefix}-pw"
    # ok: ieogagi-no-hardcoded-secret
    connect(token=f"{settings.prefix}")
    # ok: ieogagi-no-hardcoded-secret
    credentials = {"password": ""}
    # ok: ieogagi-no-hardcoded-secret
    credentials = {"password": settings.db_password, "user": "admin"}
    # ok: ieogagi-no-hardcoded-secret
    credentials = {"username": "admin", "token": os.environ["IEOGAGI_TOKEN"]}
    # ok: ieogagi-no-hardcoded-secret
    labels = {"password_label": "", "title": "Sign in"}
    # ok: ieogagi-no-hardcoded-secret
    mapping = {"role": "admin", "mode": b"rw"}
    # ok: ieogagi-no-hardcoded-secret
    api_key = os.environ["IEOGAGI_API_KEY"]
    # ok: ieogagi-no-hardcoded-secret
    secret = open("/run/secrets/session_key", encoding="utf-8").read().strip()
    # ok: ieogagi-no-hardcoded-secret
    username = "admin"
    # ok: ieogagi-no-hardcoded-secret
    connect(password=settings.db_password)


# ruleid: ieogagi-no-hardcoded-secret
def login(user, token="static-token"):
    return user, token


def tls(url, client):
    # ruleid: ieogagi-no-tls-verify-off
    requests.get(url, verify=False)
    # ruleid: ieogagi-no-tls-verify-off
    httpx.Client(verify=False)
    # ruleid: ieogagi-no-tls-verify-off
    client.post(url, verify=False)
    # ok: ieogagi-no-tls-verify-off
    requests.get(url, timeout=5)
    # ok: ieogagi-no-tls-verify-off
    requests.get(url, verify=True, timeout=5)

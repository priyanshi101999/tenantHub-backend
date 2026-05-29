import random
import secrets

def generate_otp():
    return str(random.randint(100000, 999999))

def generate_invite_token():
    return secrets.token_urlsafe(32)

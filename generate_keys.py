import secrets
import base64
import os

def generate_jwt_key(length=32):
    """Generate a random key for JWT signing"""
    return secrets.token_urlsafe(length)

def generate_encryption_key():
    """Generate a 32-byte key for AES-GCM encryption and encode it as base64"""
    # Generate 32 random bytes
    key_bytes = os.urandom(32)
    # Encode as base64
    key_b64 = base64.urlsafe_b64encode(key_bytes).decode('utf-8')
    # Remove padding
    return key_b64.rstrip('=')

# Generate keys
jwt_key = generate_jwt_key()
refresh_key = generate_jwt_key()
encryption_key = generate_encryption_key()

print(f"SECRET_KEY: {jwt_key}")
print(f"REFRESH_SECRET_KEY: {refresh_key}")
print(f"ENCRYPTION_KEY: {encryption_key}")
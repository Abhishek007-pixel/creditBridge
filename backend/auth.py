"""
CreditBridge Authentication & Encryption
- JWT tokens (HS256, 24h expiry)
- AES-256 field encryption (Fernet)
- bcrypt password hashing
- SHA-256 for Aadhaar (one-way, non-reversible)
"""
import hashlib
import os
import base64
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, DEMO_USERS
import bcrypt

# --- Password hashing ---
def hash_password(password: str) -> str:
    # Hash a password for the first time
    # (Using bcrypt, the salt is saved into the hash itself)
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    # Check hashed password. Using bcrypt, the salt is extracted from the hash.
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


# --- JWT tokens ---
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# --- AES-256 encryption ---
def _get_fernet() -> Fernet:
    """
    Derive a consistent Fernet key from SECRET_KEY.
    In production this would use a dedicated KMS-managed key.
    """
    key_bytes = hashlib.sha256(SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_field(plain_text: str) -> str:
    """Encrypt a PII field. Returns base64-encoded ciphertext."""
    if not plain_text:
        return ""
    return _get_fernet().encrypt(plain_text.encode()).decode()


def decrypt_field(encrypted_text: str) -> str:
    """Decrypt a PII field."""
    if not encrypted_text:
        return ""
    return _get_fernet().decrypt(encrypted_text.encode()).decode()


# --- Aadhaar hashing (one-way) ---
def hash_aadhaar(aadhaar_last4: str) -> str:
    """
    One-way SHA-256 hash of Aadhaar last 4 digits.
    We never store the actual digits — only the hash.
    """
    salted = f"creditbridge-aadhaar-{aadhaar_last4}-salt"
    return hashlib.sha256(salted.encode()).hexdigest()


# --- Demo user authentication ---
def authenticate_demo_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate against hardcoded demo users.
    Phase 2: Replace with DB-backed user authentication.
    """
    user = DEMO_USERS.get(username)
    if not user:
        return None
    if user["password"] != password:
        return None
    return {
        "username": username,
        "role": user["role"],
        "uid": user.get("uid", username),
        "name": user.get("name", username.split("@")[0])
    }

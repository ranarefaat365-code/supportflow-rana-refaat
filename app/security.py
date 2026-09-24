import re
import jwt
from fastapi import HTTPException
from .schemas import Principal

# Sensitive disclosures are discarded as a whole BEFORE memory, tracing, or tools.
# Deliberately conservative: no false assurance that regex detects every possible secret.
DISCLOSURE = re.compile(
    r"(?i)(?:\b(?:password|passcode|otp|one[ -]time (?:code|password)|verification code|cvv|cvc|pin)\b\s*(?:is|=|:)\s*[\"\']?[A-Za-z0-9!@#$%^&*_-]{3,})"
    r"|(?:\b(?:\d[ -]?){13,19}\b)|(?:\b\d{6}\b)"
    r"|(?:كلمة\s*(?:السر|المرور)|رمز\s*التحقق|الباسورد)\s*(?:هو|:|=)?\s*\S+"
)


def sanitize(text: str) -> str:
    if DISCLOSURE.search(text):
        return "[Sensitive disclosure removed. Please describe the issue without credentials or payment details.]"
    return text


def authenticate(token: str, settings, db) -> Principal:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
        user = db.user(payload["sub"])
        if not user:
            raise ValueError("Unknown subject")
        return Principal(**user)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            401, detail={"code": "UNAUTHENTICATED", "message": "A valid session is required."}
        ) from None


class ScopeError(Exception):
    pass


def require_scope(principal: Principal, account_id: str):
    if principal.account_id != account_id:
        raise ScopeError("Account scope mismatch")

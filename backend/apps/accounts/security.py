from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import exceptions

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from apps.accounts.models import AuthToken


ACCESS_COOKIE_NAME = "ns_access_token"
REFRESH_COOKIE_NAME = "ns_refresh_token"
LOGIN_CRYPTO_CACHE_PREFIX = "login_crypto:"
LOGIN_CRYPTO_TTL_SECONDS = 300
ACCESS_TOKEN_SECONDS = 2 * 60 * 60
REFRESH_TOKEN_SECONDS = 15 * 24 * 60 * 60


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    record: AuthToken


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token(num_bytes: int) -> str:
    return secrets.token_urlsafe(num_bytes)


def issue_tokens(user, request=None, remember_me: bool = False) -> IssuedTokens:
    access_token = generate_token(64)
    refresh_token = generate_token(64)
    now = timezone.now()
    refresh_seconds = 30 * 24 * 60 * 60 if remember_me else REFRESH_TOKEN_SECONDS
    record = AuthToken.objects.create(
        key=generate_token(32),
        user=user,
        access_token_hash=token_hash(access_token),
        refresh_token_hash=token_hash(refresh_token),
        access_expires_at=now + timedelta(seconds=ACCESS_TOKEN_SECONDS),
        refresh_expires_at=now + timedelta(seconds=refresh_seconds),
        last_used_at=now,
    )
    return IssuedTokens(access_token=access_token, refresh_token=refresh_token, record=record)


def get_access_token_from_request(request) -> str:
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if header.lower().startswith("token "):
        return header.split(" ", 1)[1].strip()
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.COOKIES.get(ACCESS_COOKIE_NAME, "")


def get_refresh_token_from_request(request) -> str:
    return request.COOKIES.get(REFRESH_COOKIE_NAME, "")


def authenticate_access_token(raw_token: str) -> AuthToken:
    if not raw_token:
        raise exceptions.AuthenticationFailed("认证信息缺失，请重新登录。")
    now = timezone.now()
    digest = token_hash(raw_token)
    try:
        record = AuthToken.objects.select_related("user").get(access_token_hash=digest, revoked_at__isnull=True)
    except AuthToken.DoesNotExist:
        try:
            record = AuthToken.objects.select_related("user").get(key=raw_token, revoked_at__isnull=True)
        except AuthToken.DoesNotExist:
            raise exceptions.AuthenticationFailed("登录状态已失效，请重新登录。")
    if record.access_expires_at and record.access_expires_at <= now:
        raise exceptions.AuthenticationFailed("登录状态已过期，请刷新后重试。")
    if not record.user.is_active:
        raise exceptions.AuthenticationFailed("账号已停用。")
    record.last_used_at = now
    record.save(update_fields=["last_used_at"])
    return record


def rotate_tokens(refresh_token: str) -> IssuedTokens:
    if not refresh_token:
        raise exceptions.AuthenticationFailed("刷新凭证缺失，请重新登录。")
    now = timezone.now()
    digest = token_hash(refresh_token)
    try:
        record = AuthToken.objects.select_related("user").get(refresh_token_hash=digest, revoked_at__isnull=True)
    except AuthToken.DoesNotExist:
        raise exceptions.AuthenticationFailed("刷新凭证已失效，请重新登录。")
    if record.refresh_expires_at and record.refresh_expires_at <= now:
        record.revoked_at = now
        record.save(update_fields=["revoked_at"])
        raise exceptions.AuthenticationFailed("登录已过期，请重新登录。")

    access_token = generate_token(64)
    new_refresh_token = generate_token(64)
    record.access_token_hash = token_hash(access_token)
    record.refresh_token_hash = token_hash(new_refresh_token)
    record.access_expires_at = now + timedelta(seconds=ACCESS_TOKEN_SECONDS)
    record.last_used_at = now
    record.save(update_fields=["access_token_hash", "refresh_token_hash", "access_expires_at", "last_used_at"])
    return IssuedTokens(access_token=access_token, refresh_token=new_refresh_token, record=record)


def revoke_token_record(record: AuthToken | None) -> None:
    if not record:
        return
    record.revoked_at = timezone.now()
    record.save(update_fields=["revoked_at"])


def cookie_secure() -> bool:
    return not getattr(settings, "DEBUG", False)


def set_auth_cookies(response, issued: IssuedTokens) -> None:
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        issued.access_token,
        max_age=ACCESS_TOKEN_SECONDS,
        httponly=True,
        secure=cookie_secure(),
        samesite="Lax",
        path="/",
    )
    refresh_max_age = int((issued.record.refresh_expires_at - timezone.now()).total_seconds()) if issued.record.refresh_expires_at else REFRESH_TOKEN_SECONDS
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        issued.refresh_token,
        max_age=max(refresh_max_age, 0),
        httponly=True,
        secure=cookie_secure(),
        samesite="Lax",
        path="/api/v1/auth/",
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", samesite="Lax")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth/", samesite="Lax")


def create_login_crypto_payload() -> dict[str, Any]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_id = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    cache.set(
        f"{LOGIN_CRYPTO_CACHE_PREFIX}{key_id}",
        {"private_key": private_pem, "nonce": nonce},
        LOGIN_CRYPTO_TTL_SECONDS,
    )
    return {"key_id": key_id, "public_key": public_pem, "nonce": nonce, "expires_in": LOGIN_CRYPTO_TTL_SECONDS}


def decrypt_login_password(*, key_id: str, nonce: str, password_cipher: str) -> str:
    cached = cache.get(f"{LOGIN_CRYPTO_CACHE_PREFIX}{key_id}")
    cache.delete(f"{LOGIN_CRYPTO_CACHE_PREFIX}{key_id}")
    if not cached or cached.get("nonce") != nonce:
        raise exceptions.ValidationError("登录加密凭证已过期，请刷新页面后重试。")
    private_key = serialization.load_pem_private_key(cached["private_key"].encode("utf-8"), password=None)
    try:
        encrypted = base64.b64decode(password_cipher)
        plain = private_key.decrypt(
            encrypted,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
    except Exception as exc:
        raise exceptions.ValidationError("密码加密数据无效，请重新登录。") from exc
    return plain.decode("utf-8")

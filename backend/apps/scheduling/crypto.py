import base64
import hashlib

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
from rest_framework import serializers


def _build_fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    """加密需要安全落库的敏感配置。"""
    return _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    """解密敏感配置，解密失败时统一返回业务错误。"""
    try:
        return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise serializers.ValidationError("敏感配置解密失败，请重新保存配置。") from exc


def mask_secret(value: str) -> str:
    """对敏感配置做脱敏展示。"""
    if not value:
        return ""
    if len(value) <= 16:
        return "****"
    return f"{value[:12]}****{value[-8:]}"

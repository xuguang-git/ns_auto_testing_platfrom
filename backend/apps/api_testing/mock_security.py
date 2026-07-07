from urllib.parse import urlencode

from django.core import signing

from apps.api_testing.models import ApiMockRule


MOCK_TOKEN_SALT = "api-mock-rule"


def mock_rule_token(rule: ApiMockRule) -> str:
    updated_at = int(rule.updated_at.timestamp()) if rule.updated_at else 0
    return signing.Signer(salt=MOCK_TOKEN_SALT).sign(f"{rule.id}:{updated_at}")


def verify_mock_rule_token(rule: ApiMockRule, token: str) -> bool:
    try:
        return signing.Signer(salt=MOCK_TOKEN_SALT).unsign(token) == mock_rule_token(rule).rsplit(":", 1)[0]
    except signing.BadSignature:
        return False


def mock_rule_path(rule: ApiMockRule, with_token: bool = False) -> str:
    path = f"/mock/api/{rule.api_id}/{rule.id}/"
    if not with_token:
        return path
    return f"{path}?{urlencode({'token': mock_rule_token(rule)})}"


def mock_proxy_path(rule: ApiMockRule, with_token: bool = False) -> str:
    api_path = str(rule.api.path or "").lstrip("/")
    path = f"/mock/proxy/{api_path}"
    if not path.endswith("/"):
        path = f"{path}/"
    if not with_token:
        return path
    return f"{path}?{urlencode({'token': mock_rule_token(rule)})}"

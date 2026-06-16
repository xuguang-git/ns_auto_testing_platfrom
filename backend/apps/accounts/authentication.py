from rest_framework import authentication, exceptions

from apps.accounts.models import AuthToken
from apps.accounts.security import authenticate_access_token, get_access_token_from_request


class StrongTokenAuthentication(authentication.BaseAuthentication):
    model = AuthToken

    def authenticate(self, request):
        raw_token = get_access_token_from_request(request)
        if not raw_token:
            return None
        token = authenticate_access_token(raw_token)
        return token.user, token

    def authenticate_header(self, request):
        return "Token"

from rest_framework import authentication, exceptions

from apps.accounts.models import AuthToken


class StrongTokenAuthentication(authentication.TokenAuthentication):
    model = AuthToken

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related("user").get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid token.")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        return token.user, token

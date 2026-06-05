from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.services import has_permission


class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        profile = getattr(user, "profile", None)
        return user.is_active and (not profile or profile.status == "active")


class HasPermissionCode(BasePermission):
    permission_map: dict[str, str] = {}

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS and getattr(view, "read_permission", None):
            code = view.read_permission
        else:
            code = getattr(view, "permission_code", None)
            if not code:
                code = self.permission_map.get(getattr(view, "basename", ""), "")
        if not code:
            return request.user and request.user.is_authenticated
        return has_permission(request.user, code)


def action_permission(read: str, write: str | None = None, delete: str | None = None):
    class ActionPermission(BasePermission):
        def has_permission(self, request, view):
            if request.method in SAFE_METHODS:
                return has_permission(request.user, read)
            if request.method == "DELETE":
                return has_permission(request.user, delete or write or read)
            return has_permission(request.user, write or read)

    return ActionPermission

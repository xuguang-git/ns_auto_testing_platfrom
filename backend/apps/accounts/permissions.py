from collections.abc import Iterable

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


EXECUTE_ACTIONS = {"debug", "run", "run_now", "check", "validate_locator", "execute", "execute_now"}


def _has_any_permission(user, codes) -> bool:
    if isinstance(codes, str):
        return has_permission(user, codes)
    if isinstance(codes, Iterable):
        return any(has_permission(user, code) for code in codes if code)
    return False


def action_permission(read, create=None, update=None, delete=None, execute=None):
    class ActionPermission(BasePermission):
        def has_permission(self, request, view):
            if request.method in SAFE_METHODS:
                return _has_any_permission(request.user, read)
            if request.method == "DELETE":
                return _has_any_permission(request.user, delete or update or create or read)
            if request.method == "POST":
                view_action = getattr(view, "action", "")
                if view_action == "create":
                    code = create
                elif view_action in EXECUTE_ACTIONS:
                    code = execute or update
                else:
                    code = update
                return _has_any_permission(request.user, code or create or read)
            return _has_any_permission(request.user, update or create or read)

    return ActionPermission

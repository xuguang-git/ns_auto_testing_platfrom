from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import decorators, mixins, response, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import AuditLog, AuthToken, LoginAttempt, Permission, Role, UserProfile, UserSession
from apps.accounts.permissions import action_permission
from apps.accounts.serializers import (
    AuditLogSerializer,
    AuthUserSerializer,
    ChangePasswordSerializer,
    LoginAttemptSerializer,
    LoginSerializer,
    PermissionSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    UserSerializer,
    UserSessionSerializer,
)
from apps.accounts.services import (
    PAGE_PERMISSION_DEFINITIONS,
    assert_user_manageable,
    create_user_session,
    ensure_builtin_roles,
    ensure_profile,
    revoke_user_sessions,
    record_failed_login,
    write_audit,
    write_login_attempt,
)
from apps.accounts.security import (
    clear_auth_cookies,
    create_login_crypto_payload,
    decrypt_login_password,
    get_refresh_token_from_request,
    issue_tokens,
    rotate_tokens,
    set_auth_cookies,
)


User = get_user_model()


class CookieAgnosticAuthentication:
    def authenticate(self, request):
        return None


class LoginCryptoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CookieAgnosticAuthentication]

    def get(self, request):
        return response.Response(create_login_crypto_payload())


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CookieAgnosticAuthentication]
    throttle_scope = "login"

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        if request.data.get("password_cipher"):
            password = decrypt_login_password(
                key_id=request.data.get("key_id", ""),
                nonce=request.data.get("nonce", ""),
                password_cipher=request.data.get("password_cipher", ""),
            )
        serializer = LoginSerializer(data={**request.data, "password": password}, context={"request": request, "password": password})
        if not serializer.is_valid():
            write_login_attempt(request, username, False, str(serializer.errors))
            try:
                record_failed_login(username)
            except DjangoPermissionDenied:
                pass
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        profile = ensure_profile(user)
        profile.failed_login_count = 0
        profile.locked_until = None
        profile.status = UserProfile.Status.ACTIVE
        profile.save(update_fields=["failed_login_count", "locked_until", "status", "updated_at"])
        AuthToken.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
        issued = issue_tokens(user, request, serializer.validated_data.get("remember_me", False))
        create_user_session(request, user, issued.record, serializer.validated_data.get("remember_me", False))
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        write_login_attempt(request, username, True)
        write_audit(request=request, user=user, action_type=AuditLog.ActionType.LOGIN, module="auth", summary="用户登录")
        resp = response.Response({"authenticated": True, "user": AuthUserSerializer(user).data})
        set_auth_cookies(resp, issued)
        return resp


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CookieAgnosticAuthentication]

    def post(self, request):
        issued = rotate_tokens(get_refresh_token_from_request(request))
        UserSession.objects.filter(token_key=issued.record.key, revoked_at__isnull=True).update(last_active_at=timezone.now())
        resp = response.Response({"authenticated": True})
        set_auth_cookies(resp, issued)
        return resp


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token_key = request.auth.key if request.auth else ""
        if token_key:
            UserSession.objects.filter(token_key=token_key, revoked_at__isnull=True).update(revoked_at=timezone.now())
            AuthToken.objects.filter(key=token_key).update(revoked_at=timezone.now())
        write_audit(request=request, action_type=AuditLog.ActionType.LOGOUT, module="auth", summary="用户退出")
        resp = response.Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(resp)
        return resp


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_profile(request.user)
        return response.Response(AuthUserSerializer(request.user).data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_profile(request.user)
        return response.Response(AuthUserSerializer(request.user).data)

    def put(self, request):
        user = request.user
        ensure_profile(user)
        data = {
            "email": request.data.get("email", user.email),
            "nickname": request.data.get("nickname", user.profile.nickname),
            "phone": request.data.get("phone", user.profile.phone),
            "avatar": request.data.get("avatar", user.profile.avatar),
        }
        serializer = UserSerializer(user, data=data, partial=True, context={"allow_protected_profile_update": True})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        write_audit(request=request, action_type=AuditLog.ActionType.UPDATE, module="profile", summary="更新个人资料")
        return response.Response(AuthUserSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        profile = ensure_profile(user)
        profile.password_changed_at = timezone.now()
        profile.must_change_password = False
        profile.save(update_fields=["password_changed_at", "must_change_password", "updated_at"])
        revoke_user_sessions(user)
        AuthToken.objects.filter(user=user).delete()
        write_audit(request=request, action_type=AuditLog.ActionType.UPDATE, module="profile", summary="修改密码")
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile", "profile__role").order_by("-date_joined", "id")
    serializer_class = UserSerializer
    filterset_fields = ["profile__role", "profile__status", "is_active"]
    search_fields = ["username", "profile__nickname", "email"]
    ordering_fields = ["date_joined", "last_login", "username"]
    permission_classes = [action_permission("user.read", "user.create", "user.update", "user.delete")]

    def list(self, request, *args, **kwargs):
        ensure_builtin_roles()
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        keyword = self.request.query_params.get("keyword")
        if keyword:
            qs = qs.filter(Q(username__icontains=keyword) | Q(profile__nickname__icontains=keyword) | Q(email__icontains=keyword))
        return qs

    def perform_create(self, serializer):
        user = serializer.save()
        write_audit(
            request=self.request,
            action_type=AuditLog.ActionType.CREATE,
            module="user",
            target_type="user",
            target_id=user.id,
            summary=f"创建用户 {user.username}",
        )

    def perform_update(self, serializer):
        user = serializer.save()
        write_audit(
            request=self.request,
            action_type=AuditLog.ActionType.UPDATE,
            module="user",
            target_type="user",
            target_id=user.id,
            summary=f"更新用户 {user.username}",
        )

    @decorators.action(detail=True, methods=["post"], url_path="enable")
    def enable(self, request, pk=None):
        user = self.get_object()
        assert_user_manageable(user, "启用")
        profile = ensure_profile(user)
        user.is_active = True
        profile.status = UserProfile.Status.ACTIVE
        user.save(update_fields=["is_active"])
        profile.save(update_fields=["status", "updated_at"])
        write_audit(request=request, action_type=AuditLog.ActionType.ENABLE, module="user", target_type="user", target_id=user.id, summary=f"启用用户 {user.username}")
        return response.Response(self.get_serializer(user).data)

    @decorators.action(detail=True, methods=["post"], url_path="disable")
    def disable(self, request, pk=None):
        user = self.get_object()
        assert_user_manageable(user, "禁用")
        if user.is_superuser and User.objects.filter(is_superuser=True, is_active=True).exclude(pk=user.pk).count() == 0:
            return response.Response({"detail": "至少保留一个启用的超级管理员"}, status=status.HTTP_400_BAD_REQUEST)
        profile = ensure_profile(user)
        user.is_active = False
        profile.status = UserProfile.Status.DISABLED
        user.save(update_fields=["is_active"])
        profile.save(update_fields=["status", "updated_at"])
        revoke_user_sessions(user)
        AuthToken.objects.filter(user=user).delete()
        write_audit(request=request, action_type=AuditLog.ActionType.DISABLE, module="user", target_type="user", target_id=user.id, summary=f"禁用用户 {user.username}")
        return response.Response(self.get_serializer(user).data)

    @decorators.action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        assert_user_manageable(user, "重置密码")
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        profile = ensure_profile(user)
        profile.password_changed_at = timezone.now()
        profile.must_change_password = serializer.validated_data["must_change_password"]
        profile.save(update_fields=["password_changed_at", "must_change_password", "updated_at"])
        revoke_user_sessions(user)
        AuthToken.objects.filter(user=user).delete()
        write_audit(request=request, action_type=AuditLog.ActionType.RESET_PASSWORD, module="user", target_type="user", target_id=user.id, summary=f"重置用户 {user.username} 密码")
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=["post"], url_path="force-logout")
    def force_logout(self, request, pk=None):
        user = self.get_object()
        assert_user_manageable(user, "强制下线")
        count = revoke_user_sessions(user)
        AuthToken.objects.filter(user=user).delete()
        write_audit(request=request, action_type=AuditLog.ActionType.FORCE_LOGOUT, module="user", target_type="user", target_id=user.id, summary=f"强制用户 {user.username} 下线")
        return response.Response({"revoked": count})

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        assert_user_manageable(user, "删除")
        user_id = user.id
        username = user.username
        result = super().destroy(request, *args, **kwargs)
        write_audit(request=request, action_type=AuditLog.ActionType.DELETE, module="user", target_type="user", target_id=user_id, summary=f"删除用户 {username}")
        return result


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions", "users").all()
    serializer_class = RoleSerializer
    filterset_fields = ["is_builtin", "is_active"]
    search_fields = ["name", "code", "description"]
    permission_classes = [action_permission("role.read", "role.create", "role.update", "role.delete")]

    def list(self, request, *args, **kwargs):
        ensure_builtin_roles()
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        role = serializer.save(is_builtin=False)
        write_audit(request=self.request, action_type=AuditLog.ActionType.CREATE, module="role", target_type="role", target_id=role.id, summary=f"创建角色 {role.name}")

    def perform_update(self, serializer):
        role = serializer.save()
        write_audit(request=self.request, action_type=AuditLog.ActionType.UPDATE, module="role", target_type="role", target_id=role.id, summary=f"更新角色 {role.name}")

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_builtin:
            return response.Response({"detail": "预置角色不可删除"}, status=status.HTTP_400_BAD_REQUEST)
        if role.users.exists():
            return response.Response({"detail": "角色已关联用户，请先调整用户角色"}, status=status.HTTP_400_BAD_REQUEST)
        write_audit(request=request, action_type=AuditLog.ActionType.DELETE, module="role", target_type="role", target_id=role.id, summary=f"删除角色 {role.name}")
        return super().destroy(request, *args, **kwargs)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [action_permission("role.read")]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        ensure_builtin_roles()
        permission_map = {item.code: item for item in Permission.objects.filter(is_visible=True)}
        return response.Response(self._permission_tree_payload(permission_map))

    def _permission_tree_payload(self, permission_map):
        payload = []
        for page in PAGE_PERMISSION_DEFINITIONS:
            tab = permission_map.get(page["code"])
            if tab:
                payload.append(self._permission_payload(tab))
            for child in page.get("children", []):
                menu = permission_map.get(child["code"])
                if menu:
                    payload.append(self._permission_payload(menu, parent_id=tab.id if tab else None))
                for action_code in child.get("actions", []):
                    action = permission_map.get(action_code)
                    if action:
                        payload.append(self._permission_payload(action, parent_id=menu.id if menu else None, sort_order=child.get("sort_order", 0)))
        return payload

    def _permission_payload(self, permission, parent_id=None, sort_order=None):
        data = PermissionSerializer(permission).data
        if parent_id is not None:
            data["parent"] = parent_id
        if sort_order is not None:
            data["sort_order"] = sort_order
        return data

    @decorators.action(detail=False, methods=["post"], url_path="sync")
    def sync(self, request):
        ensure_builtin_roles()
        return response.Response({"detail": "权限与预置角色已同步"})


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    filterset_fields = ["user", "username", "action_type", "module", "success"]
    search_fields = ["username", "summary", "target_type", "target_id"]
    ordering_fields = ["created_at"]
    permission_classes = [action_permission("audit.read")]

    @decorators.action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        rows = ["created_at,username,action_type,module,summary,ip_address,success"]
        for item in self.filter_queryset(self.get_queryset())[:10000]:
            rows.append(f"{item.created_at},{item.username},{item.action_type},{item.module},{item.summary},{item.ip_address},{item.success}")
        write_audit(request=request, action_type=AuditLog.ActionType.EXPORT, module="audit", summary="导出审计日志")
        return HttpResponse("\n".join(rows), content_type="text/csv; charset=utf-8")


class LoginAttemptViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    filterset_fields = ["username", "success", "ip_address"]
    search_fields = ["username", "reason"]
    permission_classes = [action_permission("audit.read")]


class UserSessionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="logout")
    def logout_device(self, request, pk=None):
        session = self.get_object()
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at", "updated_at"])
        if request.auth and request.auth.key == session.token_key:
            AuthToken.objects.filter(key=session.token_key).delete()
        write_audit(request=request, action_type=AuditLog.ActionType.LOGOUT, module="profile", summary="下线登录设备")
        return response.Response(status=status.HTTP_204_NO_CONTENT)

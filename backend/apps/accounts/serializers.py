from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import AuditLog, LoginAttempt, Permission, Role, UserProfile, UserSession
from apps.accounts.services import (
    ALL_PERMISSION_CODES,
    assert_user_manageable,
    ensure_builtin_roles,
    ensure_profile,
    is_protected_user,
    is_protected_username,
    protected_user_security_fix,
    validate_password_policy,
)


User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = [
            "id",
            "code",
            "module",
            "action",
            "name",
            "description",
            "type",
            "parent",
            "route_path",
            "is_visible",
            "sort_order",
        ]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(many=True, queryset=Permission.objects.all(), required=False)
    permission_codes = serializers.SerializerMethodField()
    user_count = serializers.IntegerField(source="users.count", read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "code",
            "description",
            "is_builtin",
            "is_active",
            "permissions",
            "permission_codes",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["is_builtin", "created_at", "updated_at", "permission_codes", "user_count"]

    def get_permission_codes(self, obj):
        return list(obj.permissions.values_list("code", flat=True))

    def validate_code(self, value):
        if self.instance and self.instance.is_builtin and value != self.instance.code:
            raise serializers.ValidationError("预置角色编码不可修改")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "nickname",
            "role",
            "role_name",
            "role_code",
            "phone",
            "avatar",
            "wechat_work_id",
            "status",
            "failed_login_count",
            "locked_until",
            "password_changed_at",
            "must_change_password",
        ]
        read_only_fields = ["failed_login_count", "locked_until", "password_changed_at"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_protected = serializers.SerializerMethodField()
    role = serializers.PrimaryKeyRelatedField(source="profile.role", queryset=Role.objects.all(), required=False, allow_null=True)
    role_name = serializers.CharField(source="profile.role.name", read_only=True)
    role_code = serializers.CharField(source="profile.role.code", read_only=True)
    nickname = serializers.CharField(source="profile.nickname", required=False)
    phone = serializers.CharField(source="profile.phone", required=False, allow_blank=True)
    avatar = serializers.CharField(source="profile.avatar", required=False, allow_blank=True)
    status = serializers.CharField(source="profile.status", required=False)
    wechat_work_id = serializers.CharField(source="profile.wechat_work_id", required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "is_protected",
            "last_login",
            "date_joined",
            "profile",
            "role",
            "role_name",
            "role_code",
            "nickname",
            "phone",
            "avatar",
            "status",
            "wechat_work_id",
        ]
        read_only_fields = ["id", "last_login", "date_joined", "is_staff", "is_superuser", "is_protected", "profile"]
        extra_kwargs = {"username": {"required": True}}

    def get_is_protected(self, obj):
        return is_protected_user(obj)

    def validate_username(self, value):
        if not self.instance and is_protected_username(value):
            raise serializers.ValidationError("系统保护账号不允许通过用户管理创建")
        return value

    def validate_password(self, value):
        validate_password_policy(value)
        return value

    def validate(self, attrs):
        if self.instance and is_protected_user(self.instance):
            if not self.context.get("allow_protected_profile_update"):
                assert_user_manageable(self.instance, "编辑")
            profile_data = attrs.get("profile", {})
            if "role" in profile_data:
                super_role = Role.objects.filter(code=Role.BuiltinCode.SUPER_ADMIN).first()
                if super_role and profile_data["role"] and profile_data["role"].id != super_role.id:
                    raise serializers.ValidationError({"role": "系统保护账号必须保持超级管理员角色"})
            if profile_data.get("status") and profile_data["status"] != UserProfile.Status.ACTIVE:
                raise serializers.ValidationError({"status": "系统保护账号不可禁用或锁定"})
            if attrs.get("is_active") is False:
                raise serializers.ValidationError({"is_active": "系统保护账号不可禁用"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        ensure_builtin_roles()
        profile_data = validated_data.pop("profile", {})
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        profile = ensure_profile(user, profile_data.get("role"))
        for field in ["nickname", "phone", "avatar", "wechat_work_id", "status", "role"]:
            if field in profile_data:
                setattr(profile, field, profile_data[field])
        profile.password_changed_at = timezone.now()
        profile.save()
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        ensure_builtin_roles()
        profile_data = validated_data.pop("profile", {})
        password = validated_data.pop("password", None)
        validated_data.pop("username", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if is_protected_user(instance):
            instance.is_active = True
            instance.is_staff = True
            instance.is_superuser = True
        instance.save()
        profile = ensure_profile(instance)
        if is_protected_user(instance):
            profile_data["role"] = Role.objects.get(code=Role.BuiltinCode.SUPER_ADMIN)
            profile_data["status"] = UserProfile.Status.ACTIVE
        for field in ["nickname", "phone", "avatar", "wechat_work_id", "status", "role"]:
            if field in profile_data:
                setattr(profile, field, profile_data[field])
        if password:
            profile.password_changed_at = timezone.now()
            profile.must_change_password = False
        if is_protected_user(instance):
            with protected_user_security_fix():
                profile.save()
        else:
            profile.save()
        return instance


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password_cipher = serializers.CharField(write_only=True, required=False, allow_blank=True)
    key_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    nonce = serializers.CharField(write_only=True, required=False, allow_blank=True)
    remember_me = serializers.BooleanField(default=False)

    def validate(self, attrs):
        request = self.context.get("request")
        password = attrs.get("password") or self.context.get("password") or ""
        user = authenticate(request=request, username=attrs["username"], password=password)
        if not user:
            raise serializers.ValidationError("账户密码错误，重试或联系管理员")
        profile = ensure_profile(user)
        if profile.status == UserProfile.Status.DISABLED or not user.is_active:
            raise serializers.ValidationError("账号已被禁用")
        if profile.status == UserProfile.Status.LOCKED and profile.locked_until and profile.locked_until > timezone.now():
            raise serializers.ValidationError("账号已锁定，请稍后再试")
        attrs["user"] = user
        return attrs


class AuthUserSerializer(UserSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = [field for field in UserSerializer.Meta.fields if field != "password"] + ["permissions"]

    def get_permissions(self, obj):
        profile = ensure_profile(obj)
        if obj.is_superuser:
            return ALL_PERMISSION_CODES
        if not profile.role:
            return []
        return list(profile.role.permissions.values_list("code", flat=True))


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = AuthUserSerializer()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError("当前密码不正确")
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("两次输入的新密码不一致")
        validate_password_policy(attrs["new_password"])
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    must_change_password = serializers.BooleanField(default=True)

    def validate_password(self, value):
        validate_password_policy(value)
        return value


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ["id", "device", "ip_address", "last_active_at", "expires_at", "revoked_at", "created_at", "is_active"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class LoginAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginAttempt
        fields = "__all__"

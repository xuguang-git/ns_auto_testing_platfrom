from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_migrate, pre_delete, pre_save
from django.dispatch import receiver

from apps.accounts.models import Role, UserProfile
from apps.accounts.services import allow_protected_user_security_fix, is_protected_user, protected_user_operation_message


@receiver(post_migrate)
def initialize_rbac(sender, **kwargs):
    if sender.name != "apps.accounts":
        return
    from apps.accounts.services import bootstrap_superuser_profile

    bootstrap_superuser_profile()


@receiver(pre_delete, sender=get_user_model())
def protect_builtin_user_delete(sender, instance, **kwargs):
    # 防止脚本、Django Admin 或直接 ORM 操作误删系统保护账号。
    if is_protected_user(instance):
        raise PermissionDenied(protected_user_operation_message("删除"))


@receiver(pre_save, sender=get_user_model())
def protect_builtin_user_core_fields(sender, instance, **kwargs):
    if not instance.pk or not is_protected_user(instance):
        return
    old_user = sender.objects.filter(pk=instance.pk).only("username", "is_active", "is_staff", "is_superuser").first()
    if not old_user:
        return
    if old_user.username != instance.username:
        raise PermissionDenied(protected_user_operation_message("修改用户名"))
    if not instance.is_active:
        raise PermissionDenied(protected_user_operation_message("禁用"))
    if not instance.is_staff or not instance.is_superuser:
        raise PermissionDenied(protected_user_operation_message("调整管理员身份"))


@receiver(pre_save, sender=UserProfile)
def protect_builtin_user_profile_security_fields(sender, instance, **kwargs):
    if not instance.pk or not is_protected_user(instance.user):
        return
    if allow_protected_user_security_fix():
        return
    old_profile = sender.objects.filter(pk=instance.pk).only("role_id", "status").first()
    if not old_profile:
        return
    safe_role = Role.objects.filter(pk=instance.role_id, code=Role.BuiltinCode.SUPER_ADMIN).exists()
    if old_profile.role_id != instance.role_id and not safe_role:
        raise PermissionDenied(protected_user_operation_message("调整角色"))
    if instance.status != UserProfile.Status.ACTIVE:
        raise PermissionDenied(protected_user_operation_message("调整状态"))


@receiver(pre_delete, sender=UserProfile)
def protect_builtin_user_profile_delete(sender, instance, **kwargs):
    if is_protected_user(instance.user):
        raise PermissionDenied(protected_user_operation_message("删除用户资料"))

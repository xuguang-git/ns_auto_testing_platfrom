from django.contrib.admin.apps import AdminConfig


class SecureAdminConfig(AdminConfig):
    """为项目统一替换 Django 默认 AdminSite。"""

    default_site = "config.admin.SuperuserAdminSite"

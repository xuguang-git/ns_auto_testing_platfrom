from django.contrib.admin import AdminSite


class SuperuserAdminSite(AdminSite):
    """仅向有效的 Django 超级管理员开放后台管理站点。"""

    def has_permission(self, request):
        user = request.user
        return bool(user.is_active and user.is_superuser)

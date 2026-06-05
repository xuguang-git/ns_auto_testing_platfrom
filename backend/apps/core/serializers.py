from rest_framework import serializers


class OperatorFieldsMixin(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    def get_created_by_name(self, obj):
        return self._user_display(getattr(obj, "created_by", None))

    def get_updated_by_name(self, obj):
        return self._user_display(getattr(obj, "updated_by", None))

    def _user_display(self, user):
        if not user:
            return ""
        profile = getattr(user, "profile", None)
        return getattr(profile, "nickname", "") or getattr(user, "get_full_name", lambda: "")() or user.username

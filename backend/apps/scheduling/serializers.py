from rest_framework import serializers

from apps.core.serializers import OperatorFieldsMixin
from apps.scheduling.crypto import decrypt_secret, encrypt_secret, mask_secret
from apps.scheduling.models import NotificationChannel, NotificationSendLog, NotificationTemplate, ScheduledPlan
from apps.scheduling.notification_services import TEMPLATE_VARIABLES
from apps.scheduling.services import refresh_next_run


class NotificationChannelSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    webhook = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=True)
    signature = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    webhook_mask = serializers.SerializerMethodField()
    signature_mask = serializers.SerializerMethodField()
    notification_type_display = serializers.CharField(source="get_notification_type_display", read_only=True)
    push_platform_display = serializers.CharField(source="get_push_platform_display", read_only=True)
    scheduled_plan_count = serializers.IntegerField(source="scheduled_plans.count", read_only=True)
    scheduled_plans = serializers.SerializerMethodField()

    class Meta:
        model = NotificationChannel
        fields = [
            "id",
            "name",
            "notification_type",
            "notification_type_display",
            "push_platform",
            "push_platform_display",
            "webhook",
            "webhook_mask",
            "signature",
            "signature_mask",
            "is_active",
            "scheduled_plan_count",
            "scheduled_plans",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
        ]
        read_only_fields = [
            "id",
            "webhook_mask",
            "signature_mask",
            "scheduled_plan_count",
            "scheduled_plans",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
        ]

    def get_webhook_mask(self, obj):
        return mask_secret(decrypt_secret(obj.webhook_ciphertext))

    def get_signature_mask(self, obj):
        if not obj.signature_ciphertext:
            return ""
        return mask_secret(decrypt_secret(obj.signature_ciphertext))

    def get_scheduled_plans(self, obj):
        plans = obj.scheduled_plans.order_by("next_run_at", "name").only("id", "name", "next_run_at")[:20]
        return [{"id": item.id, "name": item.name, "next_run_at": item.next_run_at} for item in plans]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("请填写通知名称。")
        if len(value) > 64:
            raise serializers.ValidationError("通知名称不能超过64个字符。")
        return value

    def validate_webhook(self, value):
        if not value.startswith("https://"):
            raise serializers.ValidationError("Webhook必须使用HTTPS地址。")
        return value

    def validate(self, attrs):
        push_platform = attrs.get("push_platform") or getattr(self.instance, "push_platform", None)
        webhook = attrs.get("webhook")
        if self.instance is None and not webhook:
            raise serializers.ValidationError({"webhook": "请填写Webhook地址。"})
        if webhook:
            self._validate_platform_webhook(push_platform, webhook)
        if push_platform != NotificationChannel.PushPlatform.FEISHU and attrs.get("signature"):
            raise serializers.ValidationError({"signature": "仅飞书通知支持签名校验。"})
        return attrs

    def _validate_platform_webhook(self, push_platform, webhook):
        platform_hosts = {
            NotificationChannel.PushPlatform.FEISHU: ("open.feishu.cn", "open.larksuite.com"),
            NotificationChannel.PushPlatform.WECHAT_WORK: ("qyapi.weixin.qq.com",),
            NotificationChannel.PushPlatform.DINGTALK: ("oapi.dingtalk.com",),
        }
        allowed_hosts = platform_hosts.get(push_platform, ())
        if allowed_hosts and not any(host in webhook for host in allowed_hosts):
            raise serializers.ValidationError({"webhook": "Webhook地址与推送平台不匹配。"})

    def create(self, validated_data):
        webhook = validated_data.pop("webhook")
        signature = validated_data.pop("signature", "")
        validated_data["webhook_ciphertext"] = encrypt_secret(webhook)
        if signature and validated_data.get("push_platform") == NotificationChannel.PushPlatform.FEISHU:
            validated_data["signature_ciphertext"] = encrypt_secret(signature)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        webhook = validated_data.pop("webhook", None)
        signature = validated_data.pop("signature", None)
        if webhook:
            instance.webhook_ciphertext = encrypt_secret(webhook)
        if signature is not None:
            instance.signature_ciphertext = encrypt_secret(signature) if signature else ""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if instance.push_platform != NotificationChannel.PushPlatform.FEISHU:
            instance.signature_ciphertext = ""
        instance.save()
        return instance


class ScheduledPlanSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    suite_name = serializers.CharField(source="suite.name", read_only=True)
    environment_name = serializers.CharField(source="environment.name", read_only=True)
    notification_names = serializers.SerializerMethodField()
    notification_template_name = serializers.CharField(source="notification_template.name", read_only=True)

    class Meta:
        model = ScheduledPlan
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "suite_name",
            "environment_name",
            "notification_names",
            "notification_template_name",
            "last_run_at",
            "next_run_at",
            "last_run_id",
            "last_status",
            "run_count",
        ]

    def get_notification_names(self, obj):
        return list(obj.notifications.values_list("name", flat=True))

    def validate_cron(self, value):
        probe = ScheduledPlan(cron=value, is_active=True)
        refresh_next_run(probe)
        return value

    def create(self, validated_data):
        notifications = validated_data.pop("notifications", [])
        instance = ScheduledPlan(**validated_data)
        refresh_next_run(instance)
        instance.save()
        instance.notifications.set(notifications)
        return instance

    def update(self, instance, validated_data):
        notifications = validated_data.pop("notifications", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        refresh_next_run(instance)
        instance.save()
        if notifications is not None:
            instance.notifications.set(notifications)
        return instance


class NotificationTemplateSerializer(OperatorFieldsMixin, serializers.ModelSerializer):
    variables = serializers.SerializerMethodField()
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    channel_platform = serializers.CharField(source="channel.push_platform", read_only=True)

    class Meta:
        model = NotificationTemplate
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "variables",
            "channel_name",
            "channel_platform",
        ]

    def get_variables(self, _obj):
        return TEMPLATE_VARIABLES

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("请填写模板名称。")
        return value

    def validate_title_template(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("请填写标题模板。")
        return value

    def validate_content_template(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("请填写内容模板。")
        return value


class NotificationSendLogSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    schedule_name = serializers.CharField(source="schedule.name", read_only=True)

    class Meta:
        model = NotificationSendLog
        fields = "__all__"
        read_only_fields = [
            "id",
            "channel",
            "template",
            "schedule",
            "test_run",
            "title",
            "content",
            "status",
            "error_message",
            "retry_count",
            "sent_at",
            "created_at",
            "updated_at",
        ]

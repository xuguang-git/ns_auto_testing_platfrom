from __future__ import annotations

import uuid

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from apps.api_testing.models import ApiDefinition, ApiImportBatch, ApiImportItem, ApiModule, HttpMethod


API_IMPORT_MAX_ITEMS_PER_BATCH = 100
API_IMPORT_QUEUE = "api_import"


def normalize_path(path: str) -> str:
    value = f"/{str(path or '').strip().lstrip('/')}"
    return value.rstrip("/") or "/"


def create_import_batch(*, module_code: str, items: list[dict], user) -> ApiImportBatch:
    module = ApiModule.objects.select_related("project", "managed_platform").filter(code=module_code, is_active=True).first()
    if not module:
        raise ValueError("模块编码不存在或已停用。")
    if len(items) > API_IMPORT_MAX_ITEMS_PER_BATCH:
        raise ValueError(f"单批最多导入 {API_IMPORT_MAX_ITEMS_PER_BATCH} 条接口。")
    snapshot = {
        "name": module.name,
        "path_names": _module_path_names(module),
        "project_name": module.project.name,
        "platform": module.platform,
    }
    with transaction.atomic():
        batch = ApiImportBatch.objects.create(
            batch_no=f"imp_{timezone.now():%Y%m%d}_{uuid.uuid4().hex[:8]}",
            module_code=module.code,
            module=module,
            module_snapshot=snapshot,
            total=len(items),
            limit_snapshot=API_IMPORT_MAX_ITEMS_PER_BATCH,
            created_by=user,
            updated_by=user,
        )
        ApiImportItem.objects.bulk_create([
            ApiImportItem(
                batch=batch,
                sequence_no=index,
                name=item["name"],
                method=item["method"],
                path=item["path"],
                normalized_path=normalize_path(item["path"]),
                params=item["params"],
            )
            for index, item in enumerate(items, start=1)
        ])
    return batch


def process_import_batch(batch_id: int, task_id: str = "") -> dict:
    batch = ApiImportBatch.objects.select_related("module", "module__project").get(pk=batch_id)
    with transaction.atomic():
        batch = ApiImportBatch.objects.select_for_update(of=("self",)).select_related("module", "module__project").get(pk=batch_id)
        if batch.status in {ApiImportBatch.Status.COMPLETED, ApiImportBatch.Status.COMPLETED_WITH_ERRORS, ApiImportBatch.Status.FAILED}:
            return batch_summary(batch)
        batch.status = ApiImportBatch.Status.RUNNING
        batch.started_at = batch.started_at or timezone.now()
        batch.celery_task_id = task_id or batch.celery_task_id
        batch.save(update_fields=["status", "started_at", "celery_task_id", "updated_at"])

    for item in batch.items.filter(status=ApiImportItem.Status.PENDING).order_by("sequence_no"):
        _process_item(batch, item)

    batch.refresh_from_db()
    counts = batch.items.values("status").order_by().annotate(count=models.Count("id"))
    counter = {item["status"]: item["count"] for item in counts}
    batch.success_count = counter.get(ApiImportItem.Status.SUCCESS, 0)
    batch.skipped_count = counter.get(ApiImportItem.Status.SKIPPED, 0)
    batch.failed_count = counter.get(ApiImportItem.Status.FAILED, 0)
    batch.finished_at = timezone.now()
    batch.status = ApiImportBatch.Status.COMPLETED if not batch.failed_count else ApiImportBatch.Status.COMPLETED_WITH_ERRORS
    batch.save(update_fields=["success_count", "skipped_count", "failed_count", "finished_at", "status", "updated_at"])
    return batch_summary(batch)


def _process_item(batch: ApiImportBatch, item: ApiImportItem) -> None:
    api = ApiDefinition.objects.filter(
        project=batch.module.project,
        platform=batch.module.platform,
        method=item.method,
        path=item.normalized_path,
    ).first()
    if api:
        item.status = ApiImportItem.Status.SKIPPED
        item.api = api
        item.params = {}
        item.save(update_fields=["status", "api", "params", "updated_at"])
        return
    try:
        payload = {
            "project": batch.module.project,
            "platform": batch.module.platform,
            "module": batch.module,
            "name": item.name,
            "method": item.method,
            "path": item.normalized_path,
            "headers": [],
            "query_params": _to_query_params(item.params) if item.method in {HttpMethod.GET, HttpMethod.DELETE} else [],
            "body_type": "json" if item.method in {HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH} else "none",
            "body": item.params if item.method in {HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH} else {},
            "created_by": batch.created_by,
            "updated_by": batch.created_by,
        }
        api = ApiDefinition.objects.create(**payload)
        item.status = ApiImportItem.Status.SUCCESS
        item.api = api
    except IntegrityError:
        item.status = ApiImportItem.Status.SKIPPED
        item.api = ApiDefinition.objects.filter(project=batch.module.project, platform=batch.module.platform, method=item.method, path=item.normalized_path).first()
    except Exception:
        item.status = ApiImportItem.Status.FAILED
    item.params = {}
    item.save(update_fields=["status", "api", "params", "updated_at"])


def _to_query_params(params: dict) -> list[dict]:
    return [{"key": key, "value": value, "enabled": True} for key, value in params.items()]


def _module_path_names(module: ApiModule) -> list[str]:
    nodes = []
    while module:
        nodes.append(module.name)
        module = module.parent
    return list(reversed(nodes))


def batch_summary(batch: ApiImportBatch) -> dict:
    return {
        "batch_no": batch.batch_no,
        "status": batch.status,
        "total": batch.total,
        "success_count": batch.success_count,
        "skipped_count": batch.skipped_count,
        "failed_count": batch.failed_count,
    }

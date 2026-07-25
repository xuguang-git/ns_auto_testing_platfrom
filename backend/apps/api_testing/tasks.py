from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.api_testing.import_services import process_import_batch
from apps.api_testing.models import ApiImportBatch, OpenApiCallLog


@shared_task(bind=True, queue="api_import", max_retries=2, soft_time_limit=300, time_limit=600, autoretry_for=(OSError,), retry_backoff=True, retry_backoff_max=300)
def process_api_import_batch(self, batch_id: int) -> dict:
    return process_import_batch(batch_id, self.request.id or "")


@shared_task
def cleanup_expired_open_api_history() -> int:
    cutoff = timezone.now() - timedelta(days=30)
    log_count, _ = OpenApiCallLog.objects.filter(created_at__lt=cutoff).delete()
    batch_count, _ = ApiImportBatch.objects.filter(
        status__in=[ApiImportBatch.Status.COMPLETED, ApiImportBatch.Status.COMPLETED_WITH_ERRORS, ApiImportBatch.Status.FAILED],
        finished_at__lt=cutoff,
    ).delete()
    return log_count + batch_count

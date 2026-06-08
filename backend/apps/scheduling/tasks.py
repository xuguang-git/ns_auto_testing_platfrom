from celery import shared_task

from apps.scheduling.services import dispatch_due_schedules


@shared_task
def dispatch_scheduled_plans() -> int:
    return dispatch_due_schedules()

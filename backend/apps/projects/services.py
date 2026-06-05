from apps.projects.models import Project


DEFAULT_PROJECT_CODE = "ns-auto"
DEFAULT_PROJECT_NAME = "NS自动化测试平台"


def get_default_project() -> Project:
    project, _ = Project.objects.get_or_create(
        code=DEFAULT_PROJECT_CODE,
        defaults={
            "name": DEFAULT_PROJECT_NAME,
            "platforms": [],
            "is_active": True,
        },
    )
    return project

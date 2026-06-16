from __future__ import annotations

from django.db import models


def apply_model_comments(model: type[models.Model], table_comment: str, field_comments: dict[str, str]) -> None:
    model._meta.db_table_comment = table_comment
    for field_name, comment in field_comments.items():
        try:
            model._meta.get_field(field_name).db_comment = comment
        except Exception:
            continue

from django.db import migrations, models


def migrate_env_credentials(apps, schema_editor):
    import base64
    import hashlib
    import os

    from cryptography.fernet import Fernet
    from django.conf import settings

    DatabaseConnection = apps.get_model("projects", "DatabaseConnection")
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    fernet = Fernet(base64.urlsafe_b64encode(digest))

    for connection in DatabaseConnection.objects.all():
        prefix = (connection.env_prefix or "").strip().upper()
        if not prefix:
            continue
        password = os.environ.get(f"{prefix}_PASSWORD", "").strip()
        connection.host = os.environ.get(f"{prefix}_HOST", "").strip()
        connection.port = int(os.environ.get(f"{prefix}_PORT") or (5432 if connection.db_type == "postgresql" else 3306))
        connection.database_name = os.environ.get(f"{prefix}_NAME", "").strip()
        connection.username = os.environ.get(f"{prefix}_USER", "").strip()
        connection.password_ciphertext = fernet.encrypt(password.encode("utf-8")).decode("utf-8") if password else ""
        connection.save(update_fields=["host", "port", "database_name", "username", "password_ciphertext"])


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0010_alter_databaseconnection_db_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="databaseconnection",
            name="env_prefix",
            field=models.SlugField(blank=True, max_length=64, unique=True),
        ),
        migrations.AddField(
            model_name="databaseconnection",
            name="host",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="databaseconnection",
            name="port",
            field=models.PositiveIntegerField(default=3306),
        ),
        migrations.AddField(
            model_name="databaseconnection",
            name="database_name",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="databaseconnection",
            name="username",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="databaseconnection",
            name="password_ciphertext",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(migrate_env_credentials, migrations.RunPython.noop),
    ]

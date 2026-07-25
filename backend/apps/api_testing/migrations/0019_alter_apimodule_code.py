from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api_testing", "0018_update_internal_api_cookie_header")]

    operations = [
        migrations.AlterField(
            model_name="apimodule",
            name="code",
            field=models.SlugField(db_comment="目录编码。", max_length=43, unique=True),
        ),
    ]

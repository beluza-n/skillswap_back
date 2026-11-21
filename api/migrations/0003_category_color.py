import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0002_reference_data")]

    operations = [
        migrations.AddField(
            model_name="category",
            name="color",
            field=models.CharField(
                default="#F3F3F3",
                max_length=7,
                validators=[django.core.validators.RegexValidator(
                    r"^#[0-9A-Fa-f]{6}$", "Укажите цвет в формате #RRGGBB."
                )],
            ),
        ),
    ]

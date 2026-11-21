from django.db import migrations


CATEGORY_COLORS = {
    "Бизнес и карьера": "#E7F2F6",
    "Иностранные языки": "#EBE5C5",
    "Дом и уют": "#FAEBD7",
    "Творчество и искусство": "#F7E7F2",
    "Образование и развитие": "#EAEAF8",
    "Здоровье и лайфстайл": "#E9F7E7",
}


def set_category_colors(apps, schema_editor):
    Category = apps.get_model("api", "Category")
    for name, color in CATEGORY_COLORS.items():
        Category.objects.filter(name=name).update(color=color)


class Migration(migrations.Migration):
    dependencies = [("api", "0003_category_color")]

    operations = [migrations.RunPython(set_category_colors, migrations.RunPython.noop)]

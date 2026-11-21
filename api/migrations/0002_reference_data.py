from django.db import migrations


# Snapshot of the Figma reference data. Keep migrations independent of live command code.
CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Пермь", "Воронеж", "Саратов",
]
SKILLS = [
    ("Бизнес и карьера", [
        "Управление командой", "Маркетинг и реклама", "Продажи и переговоры",
        "Личный бренд", "Резюме и собеседование", "Тайм-менеджмент",
        "Проектное управление", "Предпринимательство",
    ]),
    ("Иностранные языки", [
        "Английский", "Французский", "Испанский", "Немецкий", "Китайский",
        "Японский", "Подготовка к экзаменам (IELTS, TOEFL)",
    ]),
    ("Дом и уют", [
        "Уборка и организация", "Домашние финансы", "Приготовление еды",
        "Домашние растения", "Ремонт", "Хранение вещей",
    ]),
    ("Творчество и искусство", [
        "Рисование и иллюстрация", "Фотография", "Видеомонтаж", "Музыка и звук",
        "Актёрское мастерство", "Креативное письмо", "Арт-терапия", "Декор и DIY",
    ]),
    ("Образование и развитие", [
        "Личностное развитие", "Навыки обучения", "Когнитивные техники",
        "Скорочтение", "Навыки преподавания", "Коучинг",
    ]),
    ("Здоровье и лайфстайл", [
        "Йога и медитация", "Питание и ЗОЖ", "Ментальное здоровье",
        "Осознанность", "Физические тренировки", "Сон и восстановление",
        "Баланс жизни и работы",
    ]),
]


def load_reference_data(apps, schema_editor):
    City = apps.get_model("api", "City")
    Category = apps.get_model("api", "Category")
    Subcategory = apps.get_model("api", "Subcategory")
    for name in CITIES:
        City.objects.get_or_create(name=name)
    for category_sort, (name, subcategories) in enumerate(SKILLS, start=1):
        category, _ = Category.objects.update_or_create(
            name=name, defaults={"sort": category_sort}
        )
        for subcategory_sort, subcategory_name in enumerate(subcategories, start=1):
            Subcategory.objects.update_or_create(
                category=category, name=subcategory_name,
                defaults={"sort": subcategory_sort},
            )


class Migration(migrations.Migration):
    dependencies = [("api", "0001_initial")]
    operations = [migrations.RunPython(load_reference_data, migrations.RunPython.noop)]

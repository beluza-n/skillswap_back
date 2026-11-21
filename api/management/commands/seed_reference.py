from django.core.management.base import BaseCommand

from api.models import Category, City, Subcategory


SKILLS = {
    "Бизнес и карьера": [
        "Управление командой", "Маркетинг и реклама", "Продажи и переговоры",
        "Личный бренд", "Резюме и собеседование", "Тайм-менеджмент",
        "Проектное управление", "Предпринимательство",
    ],
    "Иностранные языки": [
        "Английский", "Французский", "Испанский", "Немецкий", "Китайский",
        "Японский", "Подготовка к экзаменам (IELTS, TOEFL)",
    ],
    "Дом и уют": [
        "Уборка и организация", "Домашние финансы", "Приготовление еды",
        "Домашние растения", "Ремонт", "Хранение вещей",
    ],
    "Творчество и искусство": [
        "Рисование и иллюстрация", "Фотография", "Видеомонтаж", "Музыка и звук",
        "Актёрское мастерство", "Креативное письмо", "Арт-терапия", "Декор и DIY",
    ],
    "Образование и развитие": [
        "Личностное развитие", "Навыки обучения", "Когнитивные техники",
        "Скорочтение", "Навыки преподавания", "Коучинг",
    ],
    "Здоровье и лайфстайл": [
        "Йога и медитация", "Питание и ЗОЖ", "Ментальное здоровье",
        "Осознанность", "Физические тренировки", "Сон и восстановление",
        "Баланс жизни и работы",
    ],
}

CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Пермь", "Воронеж", "Саратов",
]


class Command(BaseCommand):
    help = "Create or update the cities and skill categories used by the frontend."

    def handle(self, *args, **options):
        for name in CITIES:
            City.objects.get_or_create(name=name)
        for category_sort, (name, names) in enumerate(SKILLS.items(), start=1):
            category, _ = Category.objects.update_or_create(
                name=name, defaults={"sort": category_sort}
            )
            for subcategory_sort, subcategory_name in enumerate(names, start=1):
                Subcategory.objects.update_or_create(
                    category=category, name=subcategory_name,
                    defaults={"sort": subcategory_sort},
                )
        self.stdout.write(self.style.SUCCESS(
            f"Ready: {City.objects.count()} cities, "
            f"{Category.objects.count()} categories, {Subcategory.objects.count()} subcategories."
        ))

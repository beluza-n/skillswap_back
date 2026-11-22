"""Mirror the committed workbook and images into mock user accounts."""

import fcntl
import hashlib
import os
import re
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from PIL import Image, UnidentifiedImageError

from api.models import City, Notification, Profile, SkillImage, SkillOffer, Subcategory
from api.serializers import MAX_IMAGE_BYTES


SOURCE_DIR = Path(settings.BASE_DIR) / "mock_data"
WORKBOOK_NAME = "Моковые пользователи.xlsx"
REQUIRED_COLUMNS = (
    "mock_id", "name", "birth_date", "gender", "city", "about",
    "want_subcategories", "teach_subcategory", "skill_title", "skill_description",
)
IMAGE_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
GENDERS = {
    "мужской": "male", "женский": "female",
    "male": "male", "female": "female",
}
UNSPECIFIED_GENDERS = {"", "не указан", "unspecified"}


def text(value):
    return "" if value is None else str(value).strip()


def split_subcategories(value):
    """Split commas and semicolons, preserving commas inside parentheses."""
    result, start, depth = [], 0, 0
    for index, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char in ",;" and depth == 0:
            result.append(value[start:index].strip())
            start = index + 1
    result.append(value[start:].strip())
    return [item for item in result if item]


def parse_date(value, epoch, row_number):
    if isinstance(value, datetime):
        value = value.date()
    elif isinstance(value, (int, float)):
        value = from_excel(value, epoch=epoch)
        if isinstance(value, datetime):
            value = value.date()
    elif isinstance(value, str):
        try:
            value = date.fromisoformat(value.strip())
        except ValueError:
            try:
                value = datetime.strptime(value.strip(), "%d.%m.%Y").date()
            except ValueError as error:
                raise CommandError(f"Строка {row_number}: неверная дата рождения.") from error
    if not isinstance(value, date) or value > date.today():
        raise CommandError(f"Строка {row_number}: неверная дата рождения.")
    return value


def validate_image(path):
    expected_format = IMAGE_FORMATS.get(path.suffix.lower())
    if expected_format is None or path.stat().st_size > MAX_IMAGE_BYTES:
        raise CommandError(f"Недопустимый формат или размер изображения: {path}")
    try:
        with Image.open(path) as image:
            if image.format != expected_format:
                raise CommandError(f"Расширение не соответствует формату изображения: {path}")
            image.verify()
    except (OSError, UnidentifiedImageError) as error:
        raise CommandError(f"Повреждено изображение: {path}") from error


def image_files(mock_id):
    folder = SOURCE_DIR / mock_id
    if not folder.is_dir():
        raise CommandError(f"Не найдена папка изображений: {folder}")
    files = sorted(path for path in folder.iterdir() if path.is_file() and not path.name.startswith("."))
    avatars = [path for path in files if path.stem.lower() == "avatar"]
    if len(avatars) != 1:
        raise CommandError(f"В {folder} должен быть ровно один файл avatar.jpg/png/webp.")
    for path in files:
        validate_image(path)
    return avatars[0], [path for path in files if path != avatars[0]]


def load_records():
    workbook_path = SOURCE_DIR / WORKBOOK_NAME
    if not workbook_path.is_file():
        raise CommandError(f"Не найдена таблица: {workbook_path}")
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        if "Пользователи" not in workbook:
            raise CommandError("В таблице нет листа «Пользователи».")
        sheet = workbook["Пользователи"]
        headers = tuple(text(cell.value) for cell in sheet[2][:len(REQUIRED_COLUMNS)])
        if headers != REQUIRED_COLUMNS:
            raise CommandError("Заголовки строки 2 не совпадают с шаблоном таблицы.")
        cities = {city.name: city for city in City.objects.all()}
        subcategories = {}
        for subcategory in Subcategory.objects.all():
            if subcategory.name in subcategories:
                raise CommandError(f"Неоднозначное название подкатегории: {subcategory.name}")
            subcategories[subcategory.name] = subcategory
        records = {}
        for row_number, values in enumerate(sheet.iter_rows(min_row=3, values_only=True), start=3):
            cells = dict(zip(REQUIRED_COLUMNS, values))
            if not any(text(cells.get(key)) for key in REQUIRED_COLUMNS if key != "mock_id"):
                continue  # Pre-filled but otherwise empty rows are placeholders.
            mock_id = text(cells["mock_id"])
            if not re.fullmatch(r"user_\d+", mock_id):
                raise CommandError(f"Строка {row_number}: mock_id должен иметь вид user_41.")
            if mock_id in records:
                raise CommandError(f"Повторяется mock_id {mock_id}.")
            required = ("name", "birth_date", "city", "want_subcategories",
                        "teach_subcategory", "skill_title", "skill_description")
            for key in required:
                if not text(cells[key]):
                    raise CommandError(f"Строка {row_number}: заполните {key}.")
            gender_text = text(cells["gender"]).casefold()
            gender = None if gender_text in UNSPECIFIED_GENDERS else GENDERS.get(gender_text)
            if gender is None and gender_text not in UNSPECIFIED_GENDERS:
                raise CommandError(f"Строка {row_number}: неизвестное значение пола.")
            city_name = text(cells["city"])
            if city_name not in cities:
                raise CommandError(f"Строка {row_number}: город «{city_name}» отсутствует в справочнике.")
            teach_name = text(cells["teach_subcategory"])
            if teach_name not in subcategories:
                raise CommandError(f"Строка {row_number}: неизвестная подкатегория «{teach_name}».")
            wanted_names = split_subcategories(text(cells["want_subcategories"]))
            if not wanted_names:
                raise CommandError(f"Строка {row_number}: укажите желаемые подкатегории.")
            for name in wanted_names:
                if name not in subcategories:
                    raise CommandError(f"Строка {row_number}: неизвестная подкатегория «{name}».")
            avatar, skill_images = image_files(mock_id)
            records[mock_id] = {
                "name": text(cells["name"]),
                "birth_date": parse_date(cells["birth_date"], workbook.epoch, row_number),
                "gender": gender,
                "city": cities[city_name],
                "about": text(cells["about"]),
                "wanted_ids": list(dict.fromkeys(subcategories[name].pk for name in wanted_names)),
                "teach": subcategories[teach_name],
                "title": text(cells["skill_title"]),
                "description": text(cells["skill_description"]),
                "avatar": avatar,
                "images": skill_images,
            }
        return records
    finally:
        workbook.close()


def media_name(mock_id, source, kind):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    return f"{kind}/mock_users/{mock_id}/{source.stem}-{digest}{source.suffix.lower()}"


def ensure_media(source, name, created_files):
    if not default_storage.exists(name):
        with source.open("rb") as stream:
            stored_name = default_storage.save(name, File(stream))
        if stored_name != name:
            default_storage.delete(stored_name)
            raise CommandError(f"Не удалось сохранить изображение под именем {name}.")
        created_files.add(name)
    return name


class Command(BaseCommand):
    help = "Обновить моковых пользователей из mock_data и удалить отсутствующих в таблице."

    def handle(self, *args, **options):
        password = os.environ.get("SKILLSWAP_MOCK_PASSWORD", "")
        if len(password) < 8 or password.startswith("REPLACE_"):
            raise CommandError("Задайте SKILLSWAP_MOCK_PASSWORD длиной не менее 8 символов.")
        lock_path = Path(settings.BASE_DIR) / ".mock_users_sync.lock"
        with lock_path.open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            records = load_records()  # Validate every row and image before changing the database.
            old_media = set()
            for profile in Profile.objects.filter(mock_id__isnull=False).select_related("user"):
                if profile.avatar.name:
                    old_media.add(profile.avatar.name)
                old_media.update(
                    name for name in SkillImage.objects.filter(skill__author=profile.user)
                    .values_list("image", flat=True) if name
                )
            created_files = set()
            added = updated = 0
            try:
                with transaction.atomic():
                    for mock_id, item in records.items():
                        email = f"{mock_id}@skillswap.invalid"
                        profile = Profile.objects.select_related("user").filter(mock_id=mock_id).first()
                        if profile is None:
                            if User.objects.filter(username=email).exists():
                                raise CommandError(f"Email {email} занят обычным пользователем.")
                            user = User.objects.create_user(username=email, email=email, password=password)
                            profile = user.profile
                            added += 1
                        else:
                            user = profile.user
                            updated += 1
                        user.username = email
                        user.email = email
                        user.is_active = True
                        user.is_staff = False
                        user.is_superuser = False
                        user.set_password(password)
                        user.save()
                        profile.mock_id = mock_id
                        profile.name = item["name"]
                        profile.birth_date = item["birth_date"]
                        profile.gender = item["gender"]
                        profile.city = item["city"]
                        profile.about = item["about"]
                        profile.avatar = ensure_media(
                            item["avatar"], media_name(mock_id, item["avatar"], "avatars"),
                            created_files,
                        )
                        profile.save()
                        profile.wanted_subcategories.set(item["wanted_ids"])
                        offer, _ = SkillOffer.objects.update_or_create(
                            author=user,
                            defaults={
                                "subcategory": item["teach"],
                                "title": item["title"],
                                "description": item["description"],
                            },
                        )
                        for sort, source in enumerate(item["images"]):
                            name = ensure_media(source, media_name(mock_id, source, "skills"), created_files)
                            SkillImage.objects.update_or_create(
                                skill=offer, sort=sort, defaults={"image": name}
                            )
                        offer.images.filter(sort__gte=len(item["images"])).delete()
                    stale_profiles = Profile.objects.filter(mock_id__isnull=False).exclude(
                        mock_id__in=records
                    )
                    stale_user_ids = list(stale_profiles.values_list("user_id", flat=True))
                    if stale_user_ids:
                        Notification.objects.filter(
                            exchange_request__target_user_id__in=stale_user_ids
                        ).delete()
                        User.objects.filter(pk__in=stale_user_ids).delete()
            except Exception:
                for name in created_files:
                    default_storage.delete(name)
                raise
            current_media = set(Profile.objects.filter(mock_id__isnull=False).exclude(
                avatar=""
            ).values_list("avatar", flat=True))
            current_media.update(SkillImage.objects.filter(
                skill__author__profile__mock_id__isnull=False
            ).values_list("image", flat=True))
            for name in old_media - current_media:
                if not Profile.objects.filter(avatar=name).exists() and not SkillImage.objects.filter(image=name).exists():
                    default_storage.delete(name)
            self.stdout.write(self.style.SUCCESS(
                f"Моковые пользователи: добавлено {added}, обновлено {updated}, "
                f"удалено {len(stale_user_ids)}."
            ))

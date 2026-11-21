from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


def avatar_path(instance, filename):
    return f"avatars/{instance.user_id}/{uuid4().hex}{Path(filename).suffix.lower()}"


def skill_image_path(instance, filename):
    return f"skills/{instance.skill.author_id}/{uuid4().hex}{Path(filename).suffix.lower()}"


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Cities"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sort = models.PositiveSmallIntegerField(default=0)
    color = models.CharField(
        max_length=7,
        default="#F3F3F3",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Укажите цвет в формате #RRGGBB.")],
    )

    class Meta:
        ordering = ["sort", "id"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, related_name="subcategories", on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category__sort", "sort", "id"]
        constraints = [
            models.UniqueConstraint(fields=["category", "name"], name="unique_category_subcategory"),
        ]

    def __str__(self):
        return self.name


class Profile(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Мужской"
        FEMALE = "female", "Женский"
        UNSPECIFIED = "unspecified", "Не указан"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=12, choices=Gender.choices, default=Gender.UNSPECIFIED)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    about = models.TextField(blank=True)
    avatar = models.ImageField(upload_to=avatar_path, blank=True)
    wanted_subcategories = models.ManyToManyField(
        Subcategory, through="ProfileWantedSubcategory", related_name="learners"
    )

    def __str__(self):
        return self.name or self.user.email


class ProfileWantedSubcategory(models.Model):
    profile = models.ForeignKey(Profile, related_name="wanted_links", on_delete=models.CASCADE)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "subcategory"], name="unique_profile_wanted_subcategory"),
        ]


class SkillOffer(models.Model):
    author = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="skill_offer", on_delete=models.CASCADE)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    title = models.CharField(max_length=180)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class SkillImage(models.Model):
    skill = models.ForeignKey(SkillOffer, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to=skill_image_path)
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        constraints = [
            models.UniqueConstraint(fields=["skill", "sort"], name="unique_skill_image_sort"),
        ]


class Favorite(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="favorites", on_delete=models.CASCADE)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="favorites_received", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "target_user"], name="unique_favorite_pair"),
        ]


class ExchangeRequest(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sent_exchange_requests", on_delete=models.CASCADE)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="received_exchange_requests", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sender", "target_user"], name="unique_exchange_pair"),
        ]


class Notification(models.Model):
    class Type(models.TextChoices):
        EXCHANGE_OFFERED = "exchange_offered", "Обмен предложен"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE)
    type = models.CharField(max_length=40, choices=Type.choices)
    exchange_request = models.OneToOneField(
        ExchangeRequest, related_name="notification", null=True, blank=True, on_delete=models.SET_NULL
    )
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "read_at"], name="notification_unread_idx")]

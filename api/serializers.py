from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Category, City, Notification, Profile, SkillImage, SkillOffer, Subcategory


MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image_file(image):
    if image.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError("Изображение должно быть не больше 5 МБ.")
    if getattr(image, "content_type", "") not in {"image/jpeg", "image/png", "image/webp"}:
        raise serializers.ValidationError("Допустимы JPG, PNG и WebP.")
    return image


def image_url(image, request):
    if not image:
        return None
    return request.build_absolute_uri(image.url) if request else image.url


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name"]


class SubcategorySerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    color = serializers.CharField(source="category.color", read_only=True)

    class Meta:
        model = Subcategory
        fields = ["id", "name", "category_id", "category_name", "color", "sort"]


class SubcategoryListSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(read_only=True)
    color = serializers.CharField(source="category.color", read_only=True)

    class Meta:
        model = Subcategory
        fields = ["id", "name", "category_id", "color"]


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "sort", "color", "subcategories"]


class UserPublicSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="profile.name", read_only=True)
    age = serializers.SerializerMethodField()
    gender = serializers.CharField(source="profile.gender", read_only=True)
    city = serializers.SerializerMethodField()
    about = serializers.CharField(source="profile.about", read_only=True)
    avatar_url = serializers.SerializerMethodField()
    wanted_subcategories = SubcategorySerializer(
        source="profile.wanted_subcategories", many=True, read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id", "name", "age", "gender", "city",
            "about", "avatar_url", "wanted_subcategories",
        ]

    def get_age(self, obj):
        birth_date = obj.profile.birth_date
        if not birth_date:
            return None
        today = timezone.localdate()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )

    def get_city(self, obj):
        return obj.profile.city.name if obj.profile.city_id else None

    def get_avatar_url(self, obj):
        return image_url(obj.profile.avatar, self.context.get("request"))


class UserPrivateSerializer(UserPublicSerializer):
    city_id = serializers.IntegerField(source="profile.city_id", read_only=True)
    birth_date = serializers.DateField(source="profile.birth_date", read_only=True)
    has_unread_notifications = serializers.SerializerMethodField()

    class Meta(UserPublicSerializer.Meta):
        fields = UserPublicSerializer.Meta.fields + [
            "email", "birth_date", "city_id", "has_unread_notifications",
        ]

    def get_has_unread_notifications(self, obj):
        return obj.notifications.filter(read_at__isnull=True).exists()


class SkillImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = SkillImage
        fields = ["id", "sort", "url"]

    def get_url(self, obj):
        return image_url(obj.image, self.context.get("request"))


class SkillOfferSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)
    color = serializers.CharField(source="subcategory.category.color", read_only=True)
    images = SkillImageSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    exchange_offered = serializers.SerializerMethodField()

    class Meta:
        model = SkillOffer
        fields = [
            "id", "author", "subcategory", "color", "title", "description",
            "images", "likes_count",
            "is_liked", "exchange_offered",
        ]

    def get_likes_count(self, obj):
        if hasattr(obj, "likes_count_db"):
            return obj.likes_count_db
        return obj.author.favorites_received.count()

    def get_is_liked(self, obj):
        return obj.author_id in self.context.get("favorite_user_ids", set())

    def get_exchange_offered(self, obj):
        return obj.author_id in self.context.get("exchange_user_ids", set())


class UserSkillSerializer(serializers.ModelSerializer):
    subcategory = SubcategorySerializer(read_only=True)
    color = serializers.CharField(source="subcategory.category.color", read_only=True)
    images = SkillImageSerializer(many=True, read_only=True)

    class Meta:
        model = SkillOffer
        fields = ["title", "description", "subcategory", "color", "images"]


class UserSkillListSerializer(serializers.ModelSerializer):
    subcategory_id = serializers.IntegerField(read_only=True)
    category_id = serializers.IntegerField(source="subcategory.category_id", read_only=True)
    color = serializers.CharField(source="subcategory.category.color", read_only=True)

    class Meta:
        model = SkillOffer
        fields = ["title", "subcategory_id", "category_id", "color"]


class UserListSerializer(UserPublicSerializer):
    city_id = serializers.IntegerField(source="profile.city_id", read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    wanted_subcategories = SubcategoryListSerializer(
        source="profile.wanted_subcategories", many=True, read_only=True
    )
    skill_offer = UserSkillListSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta(UserPublicSerializer.Meta):
        fields = [
            "id", "name", "age", "gender", "city", "city_id", "about", "avatar_url",
            "date_joined", "wanted_subcategories", "skill_offer", "likes_count",
            "is_liked",
        ]

    def get_likes_count(self, obj):
        if hasattr(obj, "likes_count_db"):
            return obj.likes_count_db
        return obj.favorites_received.count()

    def get_is_liked(self, obj):
        return obj.pk in self.context.get("favorite_user_ids", set())


class UserDetailSerializer(UserPublicSerializer):
    skill_offer = UserSkillSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    exchange_offered = serializers.SerializerMethodField()

    class Meta(UserPublicSerializer.Meta):
        fields = UserPublicSerializer.Meta.fields + [
            "skill_offer", "likes_count", "is_liked", "exchange_offered",
        ]

    def get_likes_count(self, obj):
        if hasattr(obj, "likes_count_db"):
            return obj.likes_count_db
        return obj.favorites_received.count()

    def get_is_liked(self, obj):
        return obj.pk in self.context.get("favorite_user_ids", set())

    def get_exchange_offered(self, obj):
        return obj.pk in self.context.get("exchange_user_ids", set())


class NotificationSerializer(serializers.ModelSerializer):
    exchange_request_id = serializers.IntegerField(read_only=True)
    target_user_id = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "type", "message", "target_user_id", "exchange_request_id",
            "created_at", "read_at", "is_read",
        ]

    def get_target_user_id(self, obj):
        return obj.exchange_request.target_user_id if obj.exchange_request_id else None

    def get_is_read(self, obj):
        return obj.read_at is not None


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=150)
    birth_date = serializers.DateField()
    gender = serializers.ChoiceField(choices=Profile.Gender.choices, required=False, allow_null=True)
    city_id = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    about = serializers.CharField(required=False, allow_blank=True)
    wanted_subcategory_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    teach_subcategory_id = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.all())
    skill_title = serializers.CharField(max_length=180)
    skill_description = serializers.CharField()

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(username__iexact=value).exists() or User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email уже используется.")
        return value

    def validate_birth_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Дата рождения не может быть в будущем.")
        return value

    def validate_wanted_subcategory_ids(self, values):
        unique = list(dict.fromkeys(values))
        if Subcategory.objects.filter(id__in=unique).count() != len(unique):
            raise serializers.ValidationError("Одна или несколько подкатегорий не найдены.")
        return unique


class ProfileUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=150, required=False)
    name = serializers.CharField(max_length=150, required=False)
    birth_date = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=Profile.Gender.choices, required=False, allow_null=True)
    city_id = serializers.PrimaryKeyRelatedField(
        source="city", queryset=City.objects.all(), required=False, allow_null=True
    )
    about = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False, validators=[validate_image_file])

    def validate_email(self, value):
        value = value.strip().lower()
        if (
            User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists()
            or User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists()
        ):
            raise serializers.ValidationError("Email уже используется.")
        return value

    def validate_birth_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Дата рождения не может быть в будущем.")
        return value

    def update(self, instance, validated_data):
        with transaction.atomic():
            email = validated_data.pop("email", None)
            if email is not None:
                instance.username = email
                instance.email = email
                instance.save(update_fields=["username", "email"])
            profile = instance.profile
            for field, value in validated_data.items():
                setattr(profile, field, value)
            if validated_data:
                profile.save()
        return instance


class SkillOfferWriteSerializer(serializers.ModelSerializer):
    subcategory_id = serializers.PrimaryKeyRelatedField(
        source="subcategory", queryset=Subcategory.objects.all()
    )

    class Meta:
        model = SkillOffer
        fields = ["subcategory_id", "title", "description"]

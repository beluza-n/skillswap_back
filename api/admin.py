from django.contrib import admin

from .models import (
    Category, City, ExchangeRequest, Favorite, Notification, Profile,
    ProfileWantedSubcategory, SkillImage, SkillOffer, Subcategory,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "city", "gender"]
    search_fields = ["user__email", "name"]
    list_filter = ["gender", "city"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sort", "color"]


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category", "sort"]
    list_filter = ["category"]


@admin.register(SkillOffer)
class SkillOfferAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "author", "subcategory", "created_at"]
    search_fields = ["title", "author__email"]


@admin.register(SkillImage)
class SkillImageAdmin(admin.ModelAdmin):
    list_display = ["id", "skill", "sort"]


@admin.register(ProfileWantedSubcategory)
class ProfileWantedSubcategoryAdmin(admin.ModelAdmin):
    list_display = ["profile", "subcategory"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["owner", "target_user", "created_at"]


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "sender", "target_user", "created_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "type", "created_at", "read_at"]
    list_filter = ["type", "read_at"]

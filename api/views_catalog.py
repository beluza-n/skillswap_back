from django.contrib.auth.models import User
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Category, City, ExchangeRequest, Favorite, SkillOffer, Subcategory
from .serializers import CategorySerializer, CitySerializer, SubcategorySerializer, UserCardSerializer


def skill_queryset():
    return (
        SkillOffer.objects.select_related(
            "author", "author__profile", "author__profile__city",
            "subcategory", "subcategory__category"
        )
        .prefetch_related(
            "images", "author__profile__wanted_subcategories",
            "author__profile__wanted_subcategories__category",
        )
        .annotate(likes_count_db=Count("author__favorites_received", distinct=True))
    )


def skill_context(request):
    context = {"request": request, "favorite_user_ids": set(), "exchange_user_ids": set()}
    if request.user.is_authenticated:
        context["favorite_user_ids"] = set(
            Favorite.objects.filter(owner=request.user).values_list("target_user_id", flat=True)
        )
        context["exchange_user_ids"] = set(
            ExchangeRequest.objects.filter(sender=request.user).values_list("target_user_id", flat=True)
        )
    return context


def user_queryset():
    return (
        User.objects.filter(is_active=True, skill_offer__isnull=False)
        .select_related(
            "profile", "profile__city", "skill_offer",
            "skill_offer__subcategory", "skill_offer__subcategory__category",
        )
        .prefetch_related(
            "profile__wanted_subcategories",
            "profile__wanted_subcategories__category",
            "skill_offer__images",
        )
        .annotate(likes_count_db=Count("favorites_received", distinct=True))
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def cities(request):
    return Response(CitySerializer(City.objects.all(), many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def categories(request):
    rows = Category.objects.prefetch_related(
        Prefetch("subcategories", queryset=Subcategory.objects.select_related("category"))
    ).all()
    return Response(CategorySerializer(rows, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def subcategories(request):
    rows = Subcategory.objects.select_related("category").all()
    return Response(SubcategorySerializer(rows, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def users(request):
    rows = user_queryset().order_by("-date_joined", "-id")
    return Response(UserCardSerializer(rows, many=True, context=skill_context(request)).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def user_detail(request, user_id):
    user = get_object_or_404(user_queryset(), pk=user_id)
    return Response(UserCardSerializer(user, context=skill_context(request)).data)



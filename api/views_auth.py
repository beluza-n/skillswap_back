import json

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ProfileWantedSubcategory, SkillImage, SkillOffer
from .serializers import (
    ProfileUpdateSerializer,
    RegistrationSerializer, SkillOfferSerializer, SkillOfferWriteSerializer,
    UserPrivateSerializer, validate_image_file,
)
from .views_catalog import skill_context, skill_queryset


def _wanted_ids(data):
    if hasattr(data, "getlist"):
        values = data.getlist("wanted_subcategory_ids")
    else:
        values = data.get("wanted_subcategory_ids", [])
    if len(values) == 1 and isinstance(values[0], str) and values[0].startswith("["):
        try:
            values = json.loads(values[0])
        except json.JSONDecodeError:
            return values
    return values


@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def register(request):
    fields = [
        "email", "password", "name", "birth_date", "gender", "city_id",
        "about", "teach_subcategory_id", "skill_title", "skill_description",
    ]
    payload = {field: request.data.get(field) for field in fields if field in request.data}
    if payload.get("gender") == "":
        payload["gender"] = None
    payload["wanted_subcategory_ids"] = _wanted_ids(request.data)
    serializer = RegistrationSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    avatar = request.FILES.get("avatar")
    images = request.FILES.getlist("skill_images")
    image_field = serializers.ImageField(validators=[validate_image_file])
    if avatar:
        image_field.run_validation(avatar)
    for image in images:
        image_field.run_validation(image)
    data = serializer.validated_data
    with transaction.atomic():
        user = User.objects.create_user(
            username=data["email"], email=data["email"], password=data["password"],
        )
        profile = user.profile
        profile.name = data["name"]
        profile.birth_date = data["birth_date"]
        profile.gender = data.get("gender")
        profile.city = data["city_id"]
        profile.about = data.get("about", "")
        if avatar:
            profile.avatar = avatar
        profile.save()
        ProfileWantedSubcategory.objects.bulk_create([
            ProfileWantedSubcategory(profile=profile, subcategory_id=subcategory_id)
            for subcategory_id in data["wanted_subcategory_ids"]
        ])
        offer = SkillOffer.objects.create(
            author=user, subcategory=data["teach_subcategory_id"],
            title=data["skill_title"], description=data["skill_description"],
        )
        for index, image in enumerate(images):
            SkillImage.objects.create(skill=offer, image=image, sort=index)
        token = Token.objects.create(user=user)
    return Response({
        "token": token.key,
        "user": UserPrivateSerializer(user, context={"request": request}).data,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = request.data.get("password", "")
    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({"detail": "Email или пароль введён неверно."}, status=400)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "user": UserPrivateSerializer(user, context={"request": request}).data,
    })


@api_view(["POST"])
def logout(request):
    request.auth.delete()
    return Response({"ok": True})


@api_view(["GET", "PATCH"])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def me(request):
    if request.method == "GET":
        return Response(UserPrivateSerializer(request.user, context={"request": request}).data)
    old_avatar_name = request.user.profile.avatar.name if "avatar" in request.FILES else None
    serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    if old_avatar_name and old_avatar_name != request.user.profile.avatar.name:
        default_storage.delete(old_avatar_name)
    return Response(UserPrivateSerializer(request.user, context={"request": request}).data)


@api_view(["GET", "POST", "PATCH"])
def my_skill(request):
    offer = SkillOffer.objects.filter(author=request.user).first()
    if request.method == "GET":
        if offer is None:
            return Response({"detail": "Навык не найден."}, status=404)
        offer = skill_queryset().get(pk=offer.pk)
        return Response(SkillOfferSerializer(offer, context=skill_context(request)).data)
    if request.method == "POST" and offer is not None:
        return Response({"detail": "У пользователя уже есть предложение навыка."}, status=409)
    if request.method == "PATCH" and offer is None:
        return Response({"detail": "Навык не найден."}, status=404)
    serializer = SkillOfferWriteSerializer(offer, data=request.data, partial=request.method == "PATCH")
    serializer.is_valid(raise_exception=True)
    offer = serializer.save(author=request.user)
    offer = skill_queryset().get(pk=offer.pk)
    return Response(
        SkillOfferSerializer(offer, context=skill_context(request)).data,
        status=201 if request.method == "POST" else 200,
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def add_skill_image(request):
    offer = get_object_or_404(SkillOffer, author=request.user)
    image = request.FILES.get("image")
    if image is None:
        return Response({"image": ["Выберите изображение."]}, status=400)
    serializers.ImageField(validators=[validate_image_file]).run_validation(image)
    next_sort = max(offer.images.values_list("sort", flat=True), default=-1) + 1
    item = SkillImage.objects.create(skill=offer, image=image, sort=next_sort)
    from .serializers import SkillImageSerializer
    return Response(SkillImageSerializer(item, context={"request": request}).data, status=201)


@api_view(["DELETE"])
def delete_skill_image(request, image_id):
    item = get_object_or_404(SkillImage, pk=image_id, skill__author=request.user)
    image = item.image
    item.delete()
    image.delete(save=False)
    return Response(status=204)

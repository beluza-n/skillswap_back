from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ExchangeRequest, Favorite, Notification
from .serializers import NotificationSerializer, UserCardSerializer
from .views_catalog import skill_context, user_queryset


@api_view(["GET"])
def favorites(request):
    target_ids = list(
        Favorite.objects.filter(owner=request.user)
        .order_by("-created_at", "-id")
        .values_list("target_user_id", flat=True)
    )
    rows = {user.pk: user for user in user_queryset().filter(pk__in=target_ids)}
    ordered = [rows[user_id] for user_id in target_ids if user_id in rows]
    return Response(UserCardSerializer(ordered, many=True, context=skill_context(request)).data)


@api_view(["PUT"])
def set_favorite(request, user_id):
    target = get_object_or_404(User, pk=user_id, is_active=True)
    if target.pk == request.user.pk:
        return Response({"detail": "Нельзя добавить себя в избранное."}, status=400)
    desired = request.data.get("is_favorite")
    if not isinstance(desired, bool):
        return Response({"is_favorite": ["Передайте true или false."]}, status=400)
    if desired:
        Favorite.objects.get_or_create(owner=request.user, target_user=target)
    else:
        Favorite.objects.filter(owner=request.user, target_user=target).delete()
    return Response({
        "target_user_id": target.pk,
        "is_favorite": desired,
        "likes_count": Favorite.objects.filter(target_user=target).count(),
    })


@api_view(["POST"])
def create_exchange_request(request):
    target_id = request.data.get("target_user_id")
    if isinstance(target_id, bool) or not str(target_id).isdigit():
        return Response({"target_user_id": ["Передайте ID пользователя."]}, status=400)
    target = get_object_or_404(User, pk=int(target_id), is_active=True)
    if target.pk == request.user.pk:
        return Response({"detail": "Нельзя предложить обмен себе."}, status=400)
    if not hasattr(target, "skill_offer"):
        return Response({"detail": "У пользователя нет предложения навыка."}, status=400)
    with transaction.atomic():
        exchange, created = ExchangeRequest.objects.get_or_create(
            sender=request.user, target_user=target
        )
        if created:
            notification = Notification.objects.create(
                exchange_request=exchange,
                owner=request.user,
                type=Notification.Type.EXCHANGE_OFFERED,
                message=f"Вы предложили обмен {target.profile.name}",
            )
        else:
            notification = Notification.objects.filter(exchange_request=exchange).first()
    return Response({
        "exchange_request_id": exchange.pk,
        "target_user_id": target.pk,
        "exchange_offered_by_me": True,
        "notification": NotificationSerializer(notification).data if notification else None,
        "has_unread_notifications": request.user.notifications.filter(read_at__isnull=True).exists(),
    }, status=201 if created else 200)

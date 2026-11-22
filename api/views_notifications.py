from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


@api_view(["GET"])
def notifications(request):
    rows = Notification.objects.filter(owner=request.user).select_related("exchange_request")
    return Response({
        "items": NotificationSerializer(rows, many=True).data,
        "has_unread_notifications": rows.filter(read_at__isnull=True).exists(),
    })


@api_view(["POST"])
def read_all_notifications(request):
    Notification.objects.filter(
        owner=request.user, read_at__isnull=True
    ).update(read_at=timezone.now())
    return Response(status=204)


@api_view(["POST"])
def clear_notifications(request):
    Notification.objects.filter(
        owner=request.user, read_at__isnull=False
    ).delete()
    return Response(status=204)

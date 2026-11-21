from django.urls import path

from . import views_auth, views_catalog, views_notifications, views_social

urlpatterns = [
    path("auth/register/", views_auth.register),
    path("auth/login/", views_auth.login),
    path("auth/logout/", views_auth.logout),
    path("me/", views_auth.me),
    path("me/skill/", views_auth.my_skill),
    path("me/skill/images/", views_auth.add_skill_image),
    path("me/skill/images/<int:image_id>/", views_auth.delete_skill_image),
    path("cities/", views_catalog.cities),
    path("categories/", views_catalog.categories),
    path("subcategories/", views_catalog.subcategories),
    path("users/", views_catalog.users),
    path("users/<int:user_id>/", views_catalog.user_detail),
    path("favorites/", views_social.favorites),
    path("favorites/<int:user_id>/", views_social.set_favorite),
    path("exchange-requests/", views_social.create_exchange_request),
    path("notifications/", views_notifications.notifications),
    path("notifications/read-all/", views_notifications.read_all_notifications),
    path("notifications/clear/", views_notifications.clear_notifications),
]

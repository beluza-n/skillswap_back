import io
import os
import tempfile
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from api.models import Favorite, Profile


class FixedRandom:
    def __init__(self, use_maximum):
        self.use_maximum = use_maximum

    def randint(self, minimum, maximum):
        return maximum if self.use_maximum else minimum

    def sample(self, values, count):
        return values[:count]


class SyncMockUsersTests(TestCase):
    def test_dates_and_mock_likes_refresh_without_touching_real_users(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with patch.dict(os.environ, {"SKILLSWAP_MOCK_PASSWORD": "mock-test-password"}):
                with patch(
                    "api.management.commands.sync_mock_users.random.SystemRandom",
                    return_value=FixedRandom(use_maximum=True),
                ):
                    call_command("sync_mock_users", stdout=io.StringIO())

                self.assertEqual(Profile.objects.filter(mock_id__isnull=False).count(), 41)
                mock_users = list(User.objects.filter(profile__mock_id__isnull=False))
                mock_ids = [user.pk for user in mock_users]
                first = User.objects.get(profile__mock_id="user_01")
                self.assertEqual(
                    first.date_joined,
                    datetime(2026, 2, 12, tzinfo=ZoneInfo("Europe/Moscow")),
                )
                self.assertEqual(first.email, "user_01@skillswap.invalid")
                self.assertTrue(first.check_password("mock-test-password"))
                response = self.client.get("/api/users/")
                self.assertEqual(response.status_code, 200)
                api_users = response.json()
                self.assertEqual(len(api_users), 41)
                self.assertEqual(
                    next(item for item in api_users if item["id"] == first.pk)["date_joined"][:10],
                    "2026-02-12",
                )
                self.assertEqual(
                    [item["date_joined"] for item in api_users],
                    sorted((item["date_joined"] for item in api_users), reverse=True),
                )
                self.assertEqual(
                    Favorite.objects.filter(
                        owner_id__in=mock_ids, target_user_id__in=mock_ids
                    ).count(),
                    41 * 8,
                )
                for user_id in mock_ids:
                    self.assertEqual(Favorite.objects.filter(owner_id=user_id).count(), 8)
                    self.assertFalse(
                        Favorite.objects.filter(owner_id=user_id, target_user_id=user_id).exists()
                    )

                real = User.objects.create_user(
                    username="real@example.com", email="real@example.com", password="test-password"
                )
                Favorite.objects.create(owner=real, target_user=first)
                Favorite.objects.create(owner=first, target_user=real)

                with patch(
                    "api.management.commands.sync_mock_users.random.SystemRandom",
                    return_value=FixedRandom(use_maximum=False),
                ):
                    call_command("sync_mock_users", stdout=io.StringIO())

                self.assertEqual(User.objects.get(profile__mock_id="user_01").pk, first.pk)
                self.assertFalse(
                    Favorite.objects.filter(
                        owner_id__in=mock_ids, target_user_id__in=mock_ids
                    ).exists()
                )
                self.assertTrue(Favorite.objects.filter(owner=real, target_user=first).exists())
                self.assertTrue(Favorite.objects.filter(owner=first, target_user=real).exists())

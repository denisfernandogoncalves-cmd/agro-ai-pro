from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class UsersTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("gestor", is_staff=True)
        self.user = get_user_model().objects.create_user("operador")
        self.payload = {"username": "novo", "password": "Campo!Seguro2026", "password_confirmation": "Campo!Seguro2026"}

    def test_requires_admin_for_listing_and_creation(self):
        for user, expected in [(None, 401), (self.user, 403)]:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/auth/users/").status_code, expected)
            self.assertEqual(self.client.post("/api/auth/users/", self.payload).status_code, expected)

    def test_create_hashes_password_allows_login_and_never_grants_admin(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/auth/users/", {**self.payload, "is_staff": True, "is_superuser": True})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_confirmation", response.data)
        user = get_user_model().objects.get(username="novo")
        self.assertTrue(user.check_password(self.payload["password"]))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post("/api/auth/token/", self.payload).status_code, 200)

    def test_rejects_weak_mismatched_and_duplicate_credentials(self):
        self.client.force_authenticate(self.admin)
        for changes in [
            {"password": "12345678", "password_confirmation": "12345678"},
            {"password_confirmation": "diferente"},
            {"username": "gestor"},
        ]:
            self.assertEqual(self.client.post("/api/auth/users/", {**self.payload, **changes}).status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_me_and_list_do_not_expose_credentials(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/auth/users/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", str(response.data))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.get("/api/auth/me/").data["is_staff"], True)

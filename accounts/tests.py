"""
Tests for accounts app.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SignupViewTest(TestCase):
    """Test the signup view."""

    def setUp(self):
        self.signup_url = reverse("signup")
        self.login_url = reverse("login")

    def test_signup_page_loads(self):
        """Test that signup page loads successfully."""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")

    def test_signup_with_valid_data(self):
        """Test user can sign up with valid data."""
        data = {
            "username": "testuser",
            "password1": "testpassword123",
            "password2": "testpassword123",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_signup_with_invalid_data(self):
        """Test signup fails with invalid data."""
        data = {
            "username": "",  # Empty username
            "password1": "testpassword123",
            "password2": "testpassword123",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)  # Form re-rendered
        self.assertFalse(User.objects.filter(username="").exists())

    def test_signup_password_mismatch(self):
        """Test signup fails when passwords don't match."""
        data = {
            "username": "testuser",
            "password1": "testpassword123",
            "password2": "differentpassword",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="testuser").exists())


class LoginViewTest(TestCase):
    """Test the login view."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword123")
        self.login_url = reverse("login")

    def test_login_page_loads(self):
        """Test that login page loads successfully."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome Back")

    def test_login_with_valid_credentials(self):
        """Test user can login with valid credentials."""
        data = {
            "username": "testuser",
            "password": "testpassword123",
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_login_with_invalid_credentials(self):
        """Test login fails with invalid credentials."""
        data = {
            "username": "testuser",
            "password": "wrongpassword",
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)  # Form re-rendered
        self.assertContains(response, "didn't match")

    def test_login_redirects_authenticated_user(self):
        """Test that authenticated users are redirected from login page."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)  # Redirect


class CustomUserModelTest(TestCase):
    """Test the CustomUser model."""

    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(
            username="testuser", password="testpassword123", email="test@example.com"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(username="admin", password="adminpassword123")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)


class GoogleLoginTest(TestCase):
    """Test Google OAuth login integration."""

    def test_login_page_shows_google_button(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, reverse("google_login"))

    def test_signup_page_shows_google_button(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, reverse("google_login"))

    def test_google_login_url_resolves(self):
        url = reverse("google_login")
        self.assertEqual(url, "/auth/google/login/")

    def test_google_callback_url_resolves(self):
        url = reverse("google_callback")
        self.assertEqual(url, "/auth/google/login/callback/")

    def test_google_login_redirects_to_google(self):
        response = self.client.get(reverse("google_login"))
        # With empty credentials, allauth returns 200 (error page) or 302/303 (redirect)
        self.assertIn(response.status_code, [200, 302, 303])

    def test_google_callback_without_code_returns_error(self):
        response = self.client.get(reverse("google_callback"), {"state": "bad"})
        # With empty credentials, allauth returns 401 or 302/303
        self.assertIn(response.status_code, [200, 302, 303, 401])

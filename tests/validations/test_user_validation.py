import pytest
from wtforms.validators import ValidationError
from enferno.utils.validation_utils import validate_plain_text_field, validate_email_format


@pytest.fixture(scope="function")
def ensure_setup_complete(app):
    """Ensure the app is marked as set up for validation tests."""
    # Force override any config file settings
    original_value = app.config.get("SETUP_COMPLETE")
    app.config["SETUP_COMPLETE"] = True

    # Also patch the check_installation function to ensure it returns False (app is set up)
    from unittest.mock import patch

    with patch("enferno.setup.views.check_installation", return_value=False):
        yield

    # Restore original value
    app.config["SETUP_COMPLETE"] = original_value


class TestUsernameValidation:
    """Test cases for username validation."""

    def test_valid_plaintext_with_unicode(self):
        """Test that valid usernames pass validation."""
        valid_usernames = [
            "user123",
            "test_user",
            "my-username",
            "user_name-123",
            "a1b2c3",
            "test",
            "用户123",  # Chinese characters
            "пользователь",  # Cyrillic characters
            "مستخدم",  # Arabic characters
            "user_كلمة-123",  # Mixed Unicode
        ]

        for username in valid_usernames:
            # Should not raise any exception
            validate_plain_text_field(username, "Username", 32, allow_unicode=True)

    def test_valid_plaintext_without_unicode(self):
        """Test that valid usernames pass validation."""
        valid_usernames = [
            "user123",
            "testuser",
            "myusername",
            "00user",
        ]

        for username in valid_usernames:
            # Should not raise any exception
            validate_plain_text_field(username, "Username", 32, allow_unicode=False)

    def test_invalid_usernames_with_special_chars(self):
        """Test that usernames with disallowed special characters are rejected."""
        invalid_usernames = [
            "user@example",
            "test.user",
            "user+name",
            "user#123",
            "user$name",
            "user%test",
            "user&name",
            "user*123",
            "user(name)",
            "user[123]",
            "user{name}",
            "user|test",
            "user\\name",
            "user/test",
            "user?name",
            "user<>name",
            "user,name",
            "user;name",
            "user:name",
            'user"name',
            "user'name",
            "user name",  # space not allowed
        ]

        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                validate_plain_text_field(username, "Username", 32, allow_unicode=True)

    def test_invalid_usernames_with_unicode(self):
        """Test that usernames with unicode characters are rejected."""
        invalid_usernames = [
            "üser123",
            "test_user",
            "my-username",
        ]
        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                validate_plain_text_field(username, "Username", 32, allow_unicode=False)

    def test_empty_username(self):
        """Test that empty usernames are rejected."""
        with pytest.raises(ValidationError, match="Username cannot be empty"):
            validate_plain_text_field("", "Username", 32, allow_unicode=True)

        with pytest.raises(ValidationError, match="Username cannot be empty"):
            validate_plain_text_field("   ", "Username", 32, allow_unicode=True)

    @pytest.mark.parametrize(
        "url,username,error_message,field,is_checkuser",
        [
            (
                "/admin/api/checkuser/",
                "a",
                "String should have at least 4 characters",
                "item",
                True,
            ),
            (
                "/admin/api/user/",
                "a",
                "String should have at least 4 characters",
                "item.username",
                False,
            ),
            (
                "/admin/api/checkuser/",
                "a" * 256,
                "String should have at most 32 characters",
                "item",
                True,
            ),
            (
                "/admin/api/user/",
                "a" * 256,
                "String should have at most 32 characters",
                "item.username",
                False,
            ),
        ],
    )
    def test_username_length_validation(
        self,
        ensure_setup_complete,
        admin_client,
        url,
        username,
        error_message,
        field,
        is_checkuser,
    ):
        """Test username length validation using endpoints as basic format validation doesn't cover length."""
        if is_checkuser:
            payload = username
        else:
            payload = {
                "username": username,
                "email": "test@example.com",
                "name": "Test User",
                "active": True,
            }

        response = admin_client.post(url, json={"item": payload})
        assert response.status_code == 400
        assert "errors" in response.json

        # Check that the expected field error exists and contains the expected message
        assert field in response.json["errors"]
        assert error_message in response.json["errors"][field]


class TestEmailValidation:
    """Test cases for email validation."""

    def test_valid_emails(self):
        """Test that valid emails pass validation."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.net",
            "test123@test-domain.com",
            "user_name@subdomain.example.com",
            "can@göloğlu.com",
        ]

        for email in valid_emails:
            result = validate_email_format(email)
            assert "@" in result
            assert "." in result

    def test_invalid_emails(self):
        """Test that invalid emails are rejected."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@.com",
            "test@example.",
            "test space@example.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError, match="Invalid email format"):
                validate_email_format(email)

    def test_empty_email(self):
        """Test that empty emails are rejected."""
        with pytest.raises(ValidationError, match="Email cannot be empty"):
            validate_email_format("")

        with pytest.raises(ValidationError, match="Email cannot be empty"):
            validate_email_format("   ")

    def test_email_normalization(self):
        """Test that emails are normalized correctly."""
        email = "  Test.Email@EXAMPLE.COM  "
        result = validate_email_format(email)
        # Should be normalized (email-validator typically lowercases domain)
        assert result.endswith("@example.com")

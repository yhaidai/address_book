from address_book.conftest import assert_view_name_matches_url
from address_book.users.models import User


def test_user_detail(user: User):
    assert_view_name_matches_url("api:user-detail", "/api/users/{username}/", username=user.username)


def test_user_list():
    assert_view_name_matches_url("api:user-list", "/api/users/")


def test_user_me():
    assert_view_name_matches_url("api:user-me", "/api/users/me/")

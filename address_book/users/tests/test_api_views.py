from rest_framework.test import APIRequestFactory

from address_book.users.api.views import UserViewSet
from address_book.users.models import User


class TestUserViewSet:
    def test_get_queryset(self, user: User):
        request_factory = APIRequestFactory()
        view = UserViewSet()
        request = request_factory.get("/fake-url/")
        request.user = user

        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User):
        request_factory = APIRequestFactory()
        view = UserViewSet()
        request = request_factory.get("/fake-url/")
        request.user = user

        view.request = request

        response = view.me(request)  # type: ignore

        assert response.data == {
            "username": user.username,
            "name": user.name,
            "url": f"http://testserver/api/users/{user.username}/",
        }

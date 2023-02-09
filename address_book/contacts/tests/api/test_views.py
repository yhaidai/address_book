import functools
from collections import OrderedDict
from itertools import chain, combinations
from typing import Any, Callable, Iterable, TypeAlias, TypeVar
from uuid import UUID

from django.apps import apps
from django.db.models import ForeignObjectRel, Model, QuerySet

import pytest
from mypy_extensions import DefaultArg, KwArg
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from address_book.contacts.models import Contact, ContactGroup
from address_book.users.models import User

from .test_urls import (
    CONTACT_DETAIL_ENDPOINT,
    CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT,
    CONTACT_GROUP_CONTACT_LIST_ENDPOINT,
    CONTACT_GROUP_DETAIL_ENDPOINT,
    CONTACT_GROUP_LIST_ENDPOINT,
    CONTACT_GROUP_SEARCH_ENDPOINT,
    CONTACT_LIST_ENDPOINT,
)

# Typing
T = TypeVar("T")
GET_NON_EXISTENT_UUID_RETURN_TYPE: TypeAlias = Callable[[QuerySet[Any]], UUID]
POSTED_CONTACT: TypeAlias = dict[str, str | list[str]]
CONTACT_POST_DATA_FACTORY_RETURN_TYPE: TypeAlias = Callable[
    [
        DefaultArg(Iterable[str] | None),
        KwArg(Any),
    ],
    POSTED_CONTACT
]
SERIALIZED_CONTACT: TypeAlias = OrderedDict[str, str | list[UUID]]
POSTED_CONTACT_GROUP: TypeAlias = POSTED_CONTACT
CONTACT_GROUP_POST_DATA_FACTORY_RETURN_TYPE: TypeAlias = CONTACT_POST_DATA_FACTORY_RETURN_TYPE
SERIALIZED_CONTACT_GROUP: TypeAlias = SERIALIZED_CONTACT
SERIALIZED_QUERYSET = tuple[dict[str, Any], ...]

pytestmark = pytest.mark.django_db

api_client = APIClient()


def powerset(iterable: Iterable[T]) -> chain[tuple[T, ...]]:
    """powerset([1, 2, 3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def serialize_contact(contact: Contact) -> SERIALIZED_CONTACT:
    """Serialize `Contact` instance to the expected response format of an API."""
    return OrderedDict(
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone_number=str(contact.phone_number),
        contact_groups=[contact_group.uuid for contact_group in contact.contact_groups.all()],
        uuid=str(contact.uuid),
    )


def serialize_contact_group(contact_group: ContactGroup) -> SERIALIZED_CONTACT_GROUP:
    """Serialize `ContactGroup` instance to the expected response format of an API."""
    return OrderedDict(
        name=contact_group.name,
        contacts=[contact.uuid for contact in contact_group.contacts.all()],
        uuid=str(contact_group.uuid),
    )


def serialize_queryset(model_class: type[Model]) -> SERIALIZED_QUERYSET:
    """
    Serialize queryset for a given model class, including fields evaluation.

    Used to make the comparison of otherwise LAZY querysets in `assert_database_state_unchanged` trivial.
    Excludes fields for backward relationships - such relationships will be traversed anyway in a forward manner.
    """
    queryset = model_class.objects.all()
    result = tuple(
        {
            field.name: field.value_from_object(obj)  # type: ignore
            for field in model_class._meta.get_fields()
            if not isinstance(field, ForeignObjectRel)  # Skip fields for backward relationships
        }
        for obj in queryset
    )
    return result


def get_serialized_model_querysets() -> tuple[SERIALIZED_QUERYSET, ...]:
    """Return serialized querysets for all models."""
    return tuple(serialize_queryset(model_class) for model_class in apps.get_models())


def assert_database_state_unchanged(func: Callable):
    """Decorator for tests to ensure that the state of the database remains the same at the end of test execution."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        initial_querysets = get_serialized_model_querysets()

        result = func(*args, **kwargs)

        eventual_querysets = get_serialized_model_querysets()
        for initial_queryset, eventual_queryset in zip(initial_querysets, eventual_querysets):
            assert initial_queryset == eventual_queryset

        return result

    return wrapper


class TestContactListView:

    @pytest.fixture
    def contact_post_data_factory(self, contact_group_1) -> CONTACT_POST_DATA_FACTORY_RETURN_TYPE:
        """Return sample data for a 'POST /api/contacts/' request, based on the given fields."""

        def _contact_post_data(exclude: Iterable[str] | None = None, **kwargs: Any) -> POSTED_CONTACT:
            data: POSTED_CONTACT = dict(
                first_name="fn",
                last_name="ln",
                email="fnln@test.com",
                phone_number="+31682772975",
                contact_groups=[str(contact_group_1.uuid)],
            )
            data.update(kwargs)

            if exclude is not None:
                for field in exclude:
                    data.pop(field, None)  # ignore non-existing keys

            return data

        return _contact_post_data

    @assert_database_state_unchanged
    def test_get_is_not_accessible_by_anonymous_users(self):
        api_client.force_authenticate(user=None)
        response = api_client.get(CONTACT_LIST_ENDPOINT)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @assert_database_state_unchanged
    def test_get_for_authenticated_user(self, user_1: User):
        """Test that 'GET /api/contacts/' responds with 200 OK and a list of contacts for the authenticated user."""
        api_client.force_authenticate(user=user_1)
        response: Response = api_client.get(CONTACT_LIST_ENDPOINT)

        assert response.status_code == status.HTTP_200_OK
        self._assert_get_response_data_matches_users_contacts(response.data, user_1)

    @assert_database_state_unchanged
    def test_post_is_not_accessible_by_anonymous_users(
        self,
        contact_post_data_factory: CONTACT_POST_DATA_FACTORY_RETURN_TYPE,
    ):
        api_client.force_authenticate(user=None)
        response = api_client.post(CONTACT_LIST_ENDPOINT, data=contact_post_data_factory())
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "exclude", (
            # Either a first or a last name is required to create a contact, as well as
            # either an email or a phone number is required to create a contact
            *powerset(("first_name", "contact_groups", "phone_number")),
            *powerset(("last_name", "contact_groups", "phone_number")),
            *powerset(("first_name", "contact_groups", "email")),
            *powerset(("last_name", "contact_groups", "email")),
        )
    )
    def test_post_valid_data_for_authenticated_user(
        self,
        contact_post_data_factory: CONTACT_POST_DATA_FACTORY_RETURN_TYPE,
        user_1: User,
        exclude: tuple[str],
    ):
        """
        Check that 'POST /api/contacts/' with a valid data responds with 201 CREATED and an accordingly serialized
        newly created contact instance.
        """
        data = contact_post_data_factory(exclude=exclude)
        self._assert_post_response_is_ok(data=data, user=user_1)

    @pytest.mark.parametrize(
        "exclude", (
            ("first_name", "last_name"),
            ("email", "phone_number"),
        ),
    )
    @assert_database_state_unchanged
    def test_post_insufficient_data_for_authenticated_user(
        self,
        contact_post_data_factory: CONTACT_POST_DATA_FACTORY_RETURN_TYPE,
        user_1: User,
        exclude: tuple[str],
    ):
        """Check that 'POST /api/contacts/' with an insufficient data responds with 400 BAD REQUEST."""
        data = contact_post_data_factory(exclude=exclude)
        self._assert_post_response_is_bad_request(data=data, user=user_1)

    @pytest.mark.parametrize(
        "contact_post_data_factory_kwargs", (
            {"email": "invalid_email"},
            {"phone_number": "invalid_phone_number"},
            # invalid uuid is covered by `test_post_can_not_create_contact_within_not_owned_contact_group`
        )
    )
    @assert_database_state_unchanged
    def test_post_invalid_data_for_authenticated_user(
        self,
        contact_post_data_factory: CONTACT_POST_DATA_FACTORY_RETURN_TYPE,
        user_1: User,
        contact_post_data_factory_kwargs: POSTED_CONTACT,
    ):
        """Check that 'POST /api/contacts/' with an invalid data responds with 400 BAD REQUEST."""
        data = contact_post_data_factory(**contact_post_data_factory_kwargs)
        self._assert_post_response_is_bad_request(data=data, user=user_1)

    @assert_database_state_unchanged
    def test_post_can_not_create_contact_within_not_owned_contact_group(
        self,
        contact_post_data_factory: CONTACT_POST_DATA_FACTORY_RETURN_TYPE,
        user_2: User,
        contact_group_1: ContactGroup,
    ):
        """Check that 'POST /api/contacts/' with not owned contact group uuid responds with 400 BAD REQUEST."""
        data = contact_post_data_factory(contact_groups=[str(contact_group_1.uuid)])
        self._assert_post_response_is_bad_request(data=data, user=user_2)

    @staticmethod
    def _assert_get_response_data_matches_users_contacts(
        get_response_data: SERIALIZED_CONTACT,
        user: User,
    ) -> None:
        """Check that ALL user's and ONLY user's contacts are present in the response"""
        user_contacts = user.contacts.all()
        assert len(get_response_data) == len(user_contacts)
        for contact in user_contacts:
            expected_contact_data = serialize_contact(contact)
            assert expected_contact_data in get_response_data

    def _assert_post_response_is_ok(
        self,
        data: POSTED_CONTACT,
        user: User | None = None,
    ) -> None:
        """
        Check that 'POST /api/contacts/' responds with 201 CREATED and an accordingly serialized newly created contact
        instance.

        :param data: Data to be sent with the POST request
        :param user: `User` instance to authenticate under
        """
        api_client.force_authenticate(user=user)
        response = api_client.post(CONTACT_LIST_ENDPOINT, data=data)

        assert response.status_code == status.HTTP_201_CREATED
        response_data: SERIALIZED_CONTACT = response.data
        self._assert_post_data_matches_response_data(data, response_data)
        self._assert_post_response_data_is_saved_correctly(response_data, user)

    @staticmethod
    def _assert_post_response_is_bad_request(
        data: POSTED_CONTACT,
        user: User | None = None,
    ) -> None:
        """
        Check that 'POST /api/contacts/' responds with 400 BAD REQUEST.

        :param data: Data to be sent with the POST request
        :param user: `User` instance to authenticate under
        """
        api_client.force_authenticate(user=user)
        response = api_client.post(CONTACT_LIST_ENDPOINT, data=data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @staticmethod
    def _assert_post_data_matches_response_data(data: POSTED_CONTACT, response_data: SERIALIZED_CONTACT) -> None:
        """Check that data in the POST request to /api/contacts/ matches the data returned in response"""
        assert "uuid" in response_data
        data["contact_groups"] = [UUID(uuid_str) for uuid_str in data.get("contact_groups", [])]  # type: ignore
        for field, value in data.items():
            assert value == response_data[field]

    @staticmethod
    def _assert_post_response_data_is_saved_correctly(
        post_response_data: SERIALIZED_CONTACT,
        expected_user: User | None,
    ) -> None:
        """
        Check that the data returned in response to 'POST /api/contacts/' has been saved to the database correctly.

        :param expected_user: `User` instance under which the contact data was POSTed - to check it is saved to the DB
        """
        created_contact = Contact.objects.get(uuid=post_response_data["uuid"])  # type: ignore
        serialized_contact = serialize_contact(created_contact)
        assert serialized_contact == post_response_data
        assert created_contact.user == expected_user


class TestContactDetailView:

    @assert_database_state_unchanged
    def test_get_is_not_accessible_by_anonymous_users(self, contact_1: Contact):
        api_client.force_authenticate(user=None)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=contact_1.uuid)
        response: Response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @assert_database_state_unchanged
    def test_get_valid_uuid_for_authenticated_user(self, user_1: User, contact_1: Contact):
        """Test that 'GET /api/contacts/<valid_uuid>/' responds with 200 OK and a contact for the authenticated user."""
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=contact_1.uuid)
        response: Response = api_client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK
        expected_contact_data = serialize_contact(contact_1)
        assert expected_contact_data == response.data

    @assert_database_state_unchanged
    def test_get_can_not_retrieve_not_owned_contact_for_authenticated_user(
        self,
        contact_1: Contact,
        user_2: User,
    ):
        """Test that 'GET /api/contacts/<not_owned_uuid>/' responds with 404 NOT FOUND for the authenticated user."""
        api_client.force_authenticate(user=user_2)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=contact_1.uuid)
        response: Response = api_client.get(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @assert_database_state_unchanged
    def test_delete_is_not_accessible_by_anonymous_users(self, contact_1: Contact):
        api_client.force_authenticate(user=None)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=contact_1.uuid)
        response: Response = api_client.delete(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_valid_uuid_for_authenticated_user(self, user_1: User, contact_1: Contact):
        """
        Test that 'DELETE /api/contacts/<valid_uuid>/' responds with 204 NO CONTENT, and deletes the contact, as well as
        all the links to it within contact groups from the database for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=contact_1.uuid)
        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        with pytest.raises(Contact.DoesNotExist):
            Contact.objects.get(uuid=contact_1.uuid)
        assert not ContactGroup.objects.filter(contacts__uuid=contact_1.uuid)

    @assert_database_state_unchanged
    def test_delete_can_not_destroy_not_owned_contact_for_authenticated_user(
        self,
        contact_1: Contact,
        user_2: User,
    ):
        """Test that 'DELETE /api/contacts/<not_owned_uuid>/' responds with 404 NOT FOUND for the authenticated user."""
        api_client.force_authenticate(user=user_2)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=contact_1.uuid)
        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContactGroupListView:

    @pytest.fixture
    def contact_group_post_data_factory(self, contact_1) -> CONTACT_GROUP_POST_DATA_FACTORY_RETURN_TYPE:
        """Return sample data for a 'POST /api/contact_groups' request, based on the given fields."""

        def _contact_post_data(exclude: Iterable[str] | None = None, **kwargs: Any) -> POSTED_CONTACT_GROUP:
            data: POSTED_CONTACT_GROUP = dict(
                name="gn",
                contacts=[str(contact_1.uuid)],
            )
            data.update(kwargs)

            if exclude is not None:
                for field in exclude:
                    data.pop(field, None)  # ignore non-existing keys

            return data

        return _contact_post_data

    @assert_database_state_unchanged
    def test_get_is_not_accessible_by_anonymous_users(self):
        api_client.force_authenticate(user=None)
        response = api_client.get(CONTACT_GROUP_LIST_ENDPOINT)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @assert_database_state_unchanged
    def test_get_for_authenticated_user(self, user_1: User):
        """
        Test that 'GET /api/contact_groups/' responds with 200 OK and a list of contacts for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        response: Response = api_client.get(CONTACT_GROUP_LIST_ENDPOINT)

        assert response.status_code == status.HTTP_200_OK
        self._assert_get_response_data_matches_users_contact_groups(response.data, user_1)

    @assert_database_state_unchanged
    def test_post_is_not_accessible_by_anonymous_users(
        self,
        contact_group_post_data_factory: CONTACT_GROUP_POST_DATA_FACTORY_RETURN_TYPE,
    ):
        api_client.force_authenticate(user=None)
        response = api_client.post(CONTACT_GROUP_LIST_ENDPOINT, data=contact_group_post_data_factory())
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "exclude", (
            tuple(),
            ("contacts",),
        )
    )
    def test_post_valid_data_for_authenticated_user(
        self,
        contact_group_post_data_factory: CONTACT_GROUP_POST_DATA_FACTORY_RETURN_TYPE,
        user_1: User,
        exclude: tuple[str],
    ):
        """
        Check that 'POST /api/contact_groups/' with a valid data responds with 201 CREATED and an accordingly serialized
        newly created contact instance.
        """
        data = contact_group_post_data_factory(exclude=exclude)
        self._assert_post_response_is_ok(data=data, user=user_1)

    @pytest.mark.parametrize(
        "exclude", (
            ("name",),
        ),
    )
    @assert_database_state_unchanged
    def test_post_insufficient_data_for_authenticated_user(
        self,
        contact_group_post_data_factory: CONTACT_GROUP_POST_DATA_FACTORY_RETURN_TYPE,
        user_1: User,
        exclude: tuple[str],
    ):
        """Check that 'POST /api/contact_groups/' with an insufficient data responds with 400 BAD REQUEST."""
        data = contact_group_post_data_factory(exclude=exclude)
        self._assert_post_response_is_bad_request(data=data, user=user_1)

    @pytest.mark.parametrize(
        "contact_group_post_data_factory_kwargs", (
            {"name": ""},
            {"contacts": ["invalid_contact_group_uuid"]},
        )
    )
    @assert_database_state_unchanged
    def test_post_invalid_data_for_authenticated_user(
        self,
        contact_group_post_data_factory: CONTACT_GROUP_POST_DATA_FACTORY_RETURN_TYPE,
        user_1: User,
        contact_group_post_data_factory_kwargs: POSTED_CONTACT_GROUP,
    ):
        """Check that 'POST /api/contact_groups/' with an invalid data responds with 400 BAD REQUEST."""
        data = contact_group_post_data_factory(**contact_group_post_data_factory_kwargs)
        self._assert_post_response_is_bad_request(data=data, user=user_1)

    @assert_database_state_unchanged
    def test_post_can_not_create_contact_group_with_not_owned_contact(
        self,
        contact_group_post_data_factory: CONTACT_GROUP_POST_DATA_FACTORY_RETURN_TYPE,
        user_2: User,
        contact_1: ContactGroup,
    ):
        """Check that 'POST /api/contact_groups/' with not owned contact uuid responds with 400 BAD REQUEST."""
        data = contact_group_post_data_factory(contacts=[str(contact_1.uuid)])
        self._assert_post_response_is_bad_request(data=data, user=user_2)

    @staticmethod
    def _assert_get_response_data_matches_users_contact_groups(
        get_response_data: SERIALIZED_CONTACT,
        user: User,
    ) -> None:
        """Check that ALL user's and ONLY user's contact groups are present in the response"""
        user_contact_groups = user.contact_groups.all()
        assert len(get_response_data) == len(user_contact_groups)
        for contact_group in user_contact_groups:
            expected_contact_data = serialize_contact_group(contact_group)
            assert expected_contact_data in get_response_data

    def _assert_post_response_is_ok(
        self,
        data: POSTED_CONTACT_GROUP,
        user: User | None = None,
    ) -> None:
        """
        Check that 'POST /api/contact_groups/' responds with 201 CREATED and an accordingly serialized newly created
        contact group instance.

        :param data: Data to be sent with the POST request
        :param user: `User` instance to authenticate under
        """
        api_client.force_authenticate(user=user)
        response = api_client.post(CONTACT_GROUP_LIST_ENDPOINT, data=data)

        assert response.status_code == status.HTTP_201_CREATED
        response_data: SERIALIZED_CONTACT_GROUP = response.data
        self._assert_post_data_matches_response_data(data, response_data)
        self._assert_post_response_data_is_saved_correctly(response_data, user)

    @staticmethod
    def _assert_post_response_is_bad_request(
        data: POSTED_CONTACT_GROUP,
        user: User | None = None,
    ) -> None:
        """
        Check that 'POST /api/contact_groups/' responds with 400 BAD REQUEST.

        :param data: Data to be sent with the POST request
        :param user: `User` instance to authenticate under
        """
        api_client.force_authenticate(user=user)
        response = api_client.post(CONTACT_GROUP_LIST_ENDPOINT, data=data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @staticmethod
    def _assert_post_data_matches_response_data(
        data: POSTED_CONTACT_GROUP,
        response_data: SERIALIZED_CONTACT_GROUP,
    ) -> None:
        """Check that data in the POST request to /api/contact_groups/ matches the data returned in response"""
        assert "uuid" in response_data
        data["contacts"] = [UUID(uuid_str) for uuid_str in data.get("contacts", [])]  # type: ignore
        for field, value in data.items():
            assert value == response_data[field]

    @staticmethod
    def _assert_post_response_data_is_saved_correctly(
        post_response_data: SERIALIZED_CONTACT_GROUP,
        expected_user: User | None,
    ) -> None:
        """
        Check that the data returned in response to 'POST /api/contact_groups/' has been saved to the database
        correctly.

        :param expected_user: `User` instance under which the contact group data was POSTed - to check it is saved
                               to the DB
        """
        uuid = UUID(post_response_data["uuid"])  # type: ignore
        created_contact_group = ContactGroup.objects.get(uuid=uuid)
        serialized_contact_group_expected = serialize_contact_group(created_contact_group)
        assert serialized_contact_group_expected == post_response_data
        assert created_contact_group.user == expected_user


class TestContactGroupDetailView:

    @assert_database_state_unchanged
    def test_get_is_not_accessible_by_anonymous_users(self, contact_group_1: ContactGroup):
        api_client.force_authenticate(user=None)
        endpoint = CONTACT_GROUP_DETAIL_ENDPOINT.format(uuid=contact_group_1.uuid)
        response: Response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @assert_database_state_unchanged
    def test_get_valid_uuid_for_authenticated_user(
        self,
        user_1: User,
        contact_group_1: ContactGroup
    ):
        """
        Test that 'GET /api/contact_groups/<valid_uuid>/' responds with 200 OK and a contact group for the
        authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_DETAIL_ENDPOINT.format(uuid=str(contact_group_1.uuid))
        response: Response = api_client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK
        expected_contact_data = serialize_contact_group(contact_group_1)
        assert expected_contact_data == response.data

    @assert_database_state_unchanged
    def test_get_can_not_retrieve_not_owned_contact_group_for_authenticated_user(
        self,
        contact_group_1: ContactGroup,
        user_2: User,
    ):
        """
        Test that 'GET /api/contact_groups/<not_owned_uuid>/' responds with 404 NOT FOUND for the authenticated user.
        """
        api_client.force_authenticate(user=user_2)
        endpoint = CONTACT_GROUP_DETAIL_ENDPOINT.format(uuid=contact_group_1.uuid)
        response: Response = api_client.get(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @assert_database_state_unchanged
    def test_delete_is_not_accessible_by_anonymous_users(self, contact_1: Contact):
        api_client.force_authenticate(user=None)
        endpoint = CONTACT_GROUP_DETAIL_ENDPOINT.format(uuid=contact_1.uuid)
        response: Response = api_client.delete(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_valid_uuid_for_authenticated_user(self, user_1: User, contact_group_1: ContactGroup):
        """
        Test that 'DELETE /api/contact_groups/<valid_uuid>/' responds with 204 NO CONTENT, and deletes the contact
        group, as well as all the links to it within contacts from the database for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_DETAIL_ENDPOINT.format(uuid=contact_group_1.uuid)
        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        with pytest.raises(ContactGroup.DoesNotExist):
            ContactGroup.objects.get(uuid=contact_group_1.uuid)
        assert not Contact.objects.filter(contact_group__uuid=contact_group_1.uuid)

    @assert_database_state_unchanged
    def test_delete_can_not_destroy_not_owned_contact_group_for_authenticated_user(
        self,
        contact_group_1: ContactGroup,
        user_2: User,
    ):
        """
        Test that 'DELETE /api/contact_groups/<not_owned_uuid>/' responds with 404 NOT FOUND, and an expected message
        for the authenticated user.
        """
        api_client.force_authenticate(user=user_2)
        endpoint = CONTACT_GROUP_DETAIL_ENDPOINT.format(uuid=contact_group_1.uuid)
        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContactGroupRemoveContactView:

    @assert_database_state_unchanged
    def test_delete_is_not_accessible_by_anonymous_users(self, contact_1: Contact, contact_group_1: ContactGroup):
        api_client.force_authenticate(user=None)
        endpoint = CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT.format(
            contact_group_uuid=str(contact_group_1.uuid),
            contact_uuid=str(contact_1.uuid),
        )
        response: Response = api_client.delete(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_valid_uuid_for_authenticated_user(
        self,
        user_1: User,
        contact_1: Contact,
        contact_group_1: ContactGroup,
    ):
        """
        Test that 'DELETE /api/contact_groups/<valid_group_uuid>/contacts/<valid_contact_uuid>' responds with
        204 NO CONTENT, and the link between contact and group is removed, however the contact itself still remains.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT.format(
            contact_group_uuid=contact_group_1.uuid,
            contact_uuid=contact_1.uuid,
        )
        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        with pytest.raises(Contact.DoesNotExist):
            contact_group_1.contacts.get(uuid=contact_1.uuid)
        with pytest.raises(ContactGroup.DoesNotExist):
            contact_1.contact_groups.get(uuid=contact_group_1.uuid)
        assert user_1.contacts.filter(uuid=contact_1.uuid)

    @assert_database_state_unchanged
    def test_delete_can_not_destroy_not_owned_contact_for_authenticated_user(
        self,
        contact_5: Contact,
        contact_group_1: ContactGroup,
        user_1: User,
    ):
        """
        Test that 'DELETE /api/contact_groups/<valid_group_uuid>/contacts/<not_owned_contact_uuid>' responds with
        404 NOT FOUND and an expected message for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT.format(
            contact_group_uuid=contact_group_1.uuid,
            contact_uuid=contact_5.uuid,
        )

        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {
            "detail": f"Contact with UUID '{contact_5.uuid}' does not exist for your user.",
        }

    @assert_database_state_unchanged
    def test_delete_can_not_destroy_owned_contact_within_not_owned_contact_group_for_authenticated_user(
        self,
        contact_1: Contact,
        contact_group_3: ContactGroup,
        user_1: User,
    ):
        """
        Test that 'DELETE /api/contact_groups/<not_owned_contact_group_uuid>/contacts/<valid_contact_uuid>' responds
        with 404 NOT FOUND and an expected message for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT.format(
            contact_group_uuid=contact_group_3.uuid,
            contact_uuid=contact_1.uuid,
        )

        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {
            "detail": f"ContactGroup with UUID '{contact_group_3.uuid}' does not exist for your user.",
        }

    @assert_database_state_unchanged
    def test_delete_can_not_destroy_not_owned_contact_within_its_contact_group_for_authenticated_user(
        self,
        contact_1: Contact,
        contact_group_1: ContactGroup,
        user_2: User,
    ):
        """
        Test that 'DELETE /api/contact_groups/<not_owned_contact_group_uuid>/contacts/<not_owned_contact_uuid>' responds
        with 404 NOT FOUND for the authenticated user.
        """

        api_client.force_authenticate(user=user_2)
        endpoint = CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT.format(
            contact_group_uuid=contact_group_1.uuid,
            contact_uuid=contact_1.uuid,
        )
        response: Response = api_client.delete(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContactGroupAddListContactsView:

    @assert_database_state_unchanged
    def test_get_is_not_accessible_by_anonymous_users(self, contact_group_1: ContactGroup):
        api_client.force_authenticate(user=None)
        endpoint = CONTACT_GROUP_CONTACT_LIST_ENDPOINT.format(contact_group_uuid=contact_group_1.uuid)
        response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @assert_database_state_unchanged
    def test_get_valid_uuid_for_authenticated_user(self, user_1: User, contact_group_1: ContactGroup):
        """
        Test that 'GET /api/contact_groups/<valid_uuid>/contacts/' responds with 200 OK and a list of contacts
        for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_LIST_ENDPOINT.format(contact_group_uuid=contact_group_1.uuid)
        response: Response = api_client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK
        self._assert_get_response_data_matches_groups_contacts(response.data, contact_group_1)

    @assert_database_state_unchanged
    def test_get_not_owned_uuid_for_authenticated_user(self, user_1: User, contact_group_3: ContactGroup):
        """
        Test that 'GET /api/contact_groups/<not_owned_uuid>/contacts/' responds with 200 OK and a list of contacts
        for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_LIST_ENDPOINT.format(contact_group_uuid=contact_group_3.uuid)
        response: Response = api_client.get(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @assert_database_state_unchanged
    def test_post_is_not_accessible_by_anonymous_users(self, contact_group_1: ContactGroup, contact_4: Contact):
        api_client.force_authenticate(user=None)
        endpoint = CONTACT_GROUP_CONTACT_LIST_ENDPOINT.format(contact_group_uuid=contact_group_1.uuid)
        response = api_client.post(endpoint, data={"uuid": str(contact_4.uuid)})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @assert_database_state_unchanged
    def test_post_can_not_add_contact_to_not_owned_contact_group_for_authenticated_user(
        self,
        user_1: User,
        contact_group_3: ContactGroup,
        contact_4: Contact,
    ):
        """
        Test that 'POST /api/contact_groups/<not_owned_uuid>/contacts/ {"uuid": "<owned_contact_uuid>"}' responds with
        404 NOT FOUND and an expected message for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_LIST_ENDPOINT.format(contact_group_uuid=contact_group_3.uuid)
        response = api_client.post(endpoint, data={"uuid": str(contact_4.uuid)})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {
            "detail": f"ContactGroup with UUID '{contact_group_3.uuid}' does not exist for your user."
        }

    @assert_database_state_unchanged
    def test_post_can_not_add_not_owned_contact_to_owned_contact_group_for_authenticated_user(
        self,
        user_1: User,
        contact_group_1: ContactGroup,
        contact_5: Contact,
    ):
        """
        Test that 'POST /api/contact_groups/<owned_uuid>/contacts/ {"uuid": "<not_owned_contact_uuid>"}' responds with
        404 NOT FOUND and an expected message for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_LIST_ENDPOINT.format(contact_group_uuid=contact_group_1.uuid)
        response = api_client.post(endpoint, data={"uuid": str(contact_5.uuid)})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {
            "detail": f"Contact with UUID '{contact_5.uuid}' does not exist for your user."
        }

    def test_post_valid_data_for_authenticated_user(
        self,
        contact_4: Contact,
        contact_group_1: ContactGroup,
        user_1: User,
    ):
        """
        Check that 'POST /api/contact_groups/<valid_uuid>/contacts/' with a valid data responds with 200 OK and an
        accordingly serialized contact instance, which was added to the group.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_GROUP_CONTACT_LIST_ENDPOINT.format(contact_group_uuid=contact_group_1.uuid)
        contact_uuid_str = str(contact_4.uuid)
        response = api_client.post(endpoint, data={"uuid": contact_uuid_str})

        assert response.status_code == status.HTTP_200_OK
        response_data: SERIALIZED_CONTACT = response.data

        # Response data must correspond to the POSTed data
        assert contact_uuid_str == response_data["uuid"]

        # Response data must correspond to the actual contact with the UUID which was POSTed
        added_contact: Contact = Contact.objects.get(uuid=contact_uuid_str)
        serialized_contact = serialize_contact(added_contact)
        assert serialized_contact == response_data

        # Target contact and group should now be linked
        assert contact_group_1 in added_contact.contact_groups.all()
        assert added_contact in contact_group_1.contacts.all()

    @assert_database_state_unchanged
    def test_post_insufficient_data_for_authenticated_user(
        self,
        user_1: User,
        contact_group_1: ContactGroup,
    ):
        """
        Check that ''POST /api/contact_groups/<valid_uuid>/contacts/' with an insufficient data responds with
        400 BAD REQUEST.
        """
        api_client.force_authenticate(user=user_1)
        response = api_client.post(CONTACT_GROUP_LIST_ENDPOINT, data={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @staticmethod
    def _assert_get_response_data_matches_groups_contacts(
        get_response_data: SERIALIZED_CONTACT,
        contact_group: ContactGroup,
    ) -> None:
        """Check that ALL contacts of the group and ONLY contacts of the group are present in the response."""
        contact_group_contacts = contact_group.contacts.all()
        assert len(get_response_data) == len(contact_group_contacts)
        for contact in contact_group_contacts:
            expected_contact_data = serialize_contact(contact)
            assert expected_contact_data in get_response_data


class TestContactGroupSearchView:
    @assert_database_state_unchanged
    def test_get_is_not_accessible_by_anonymous_users(self, contact_group_1: ContactGroup):
        api_client.force_authenticate(user=None)
        endpoint = f"{CONTACT_GROUP_SEARCH_ENDPOINT}?name={contact_group_1.name}"
        response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "name_query",
        ("1", "2", "group", "con", "")
    )
    @assert_database_state_unchanged
    def test_get_valid_uuid_for_authenticated_user(self, user_1: User, contact_group_1: ContactGroup, name_query: str):
        """
        Test that 'GET /api/contact_groups/search?name=<name_query>' responds with 200 OK and a list of contact groups
        for the authenticated user.
        """
        api_client.force_authenticate(user=user_1)
        endpoint = f"{CONTACT_GROUP_SEARCH_ENDPOINT}?name={name_query}"
        response: Response = api_client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK
        self._assert_get_response_data_matches_search_results(response.data, user_1, name_query)

    @staticmethod
    def _assert_get_response_data_matches_search_results(
        get_response_data: SERIALIZED_CONTACT,
        user: User,
        name_query: str,
    ) -> None:
        """Check that ALL user's and ONLY user's contact groups are present in the response"""
        contact_groups = ContactGroup.objects.filter(user=user, name__contains=name_query).all()
        assert len(get_response_data) == len(contact_groups)
        for contact_group in contact_groups:
            expected_contact_data = serialize_contact_group(contact_group)
            assert expected_contact_data in get_response_data

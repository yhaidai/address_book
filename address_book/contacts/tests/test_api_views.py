from collections import OrderedDict
from itertools import chain, combinations
from typing import Any, Callable, Iterable, TypeAlias, TypeVar
from uuid import UUID, uuid4

from django.db.models import QuerySet

import pytest
from mypy_extensions import KwArg, DefaultArg
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from address_book.contacts.models import Contact, ContactGroup
from address_book.users.models import User

CONTACT_LIST_ENDPOINT = "/api/contacts/"
CONTACT_DETAIL_ENDPOINT = "/api/contacts/{uuid}"
CONTACT_GROUPS_ENDPOINT = "/api/contact_groups/"

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
SERIALIZE_CONTACT_RETURN_TYPE: TypeAlias = Callable[[Contact], SERIALIZED_CONTACT]

pytestmark = pytest.mark.django_db


def powerset(iterable: Iterable[T]) -> chain[tuple[T, ...]]:
    """powerset([1, 2, 3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


@pytest.fixture
def user_1() -> User:
    """User that has contacts 1-4, and contact groups 1-2."""
    return User.objects.create(
        name="Test User 1",
        username="test_username_1",
        email="user_1@test.com",
    )


@pytest.fixture
def user_2() -> User:
    return User.objects.create(
        name="Test User 2",
        username="test_username_2",
        email="user_2@test.com",
    )


@pytest.fixture
def contact_1(user_1: User) -> Contact:
    """Contact of `user_1`, belongs to `contact_group_1` and `contact_group_2`."""
    return Contact.objects.create(
        first_name="first name 1",
        last_name="last name 1",
        email="contact_1@test.com",
        phone_number="+31111111111",
        user=user_1,
    )


@pytest.fixture
def contact_2(user_1: User) -> Contact:
    """Contact of `user_1`, belongs to `contact_group_1`."""
    return Contact.objects.create(
        first_name="first name 2",
        last_name="last name 2",
        email="contact_2@test.com",
        phone_number="+31222222222",
        user=user_1,
    )


@pytest.fixture
def contact_3(user_1: User) -> Contact:
    """Contact of `user_1`, belongs to `contact_group_2`."""
    return Contact.objects.create(
        first_name="first name 3",
        last_name="last name 3",
        email="contact_3@test.com",
        phone_number="+31333333333",
        user=user_1,
    )


@pytest.fixture
def contact_4(user_1: User) -> Contact:
    """Contact of `user_1`, doesn't belong to any group."""
    return Contact.objects.create(
        first_name="first name 4",
        last_name="last name 4",
        email="contact_4@test.com",
        phone_number="+31444444444",
        user=user_1,
    )


@pytest.fixture
def contact_group_1(user_1: User, contact_1: Contact, contact_2: Contact) -> ContactGroup:
    """Contact group of `user_1`, contains `contact_1`, `contact_2`."""
    contact_group = ContactGroup.objects.create(
        name="contact group 1",
        user=user_1,
    )
    contact_group.contacts.set([
        contact_1,
        contact_2,
    ])
    return contact_group


@pytest.fixture
def contact_group_2(user_1: User, contact_1: Contact, contact_3: Contact) -> ContactGroup:
    """Contact group of `user_1`, contains `contact_1`, `contact_3`."""
    contact_group = ContactGroup.objects.create(
        name="contact group 2",
        user=user_1,
    )
    contact_group.contacts.set([
        contact_1,
        contact_3,
    ])
    return contact_group


@pytest.fixture(autouse=True)
def create_test_model_instances(contact_group_1: ContactGroup, contact_group_2: ContactGroup) -> None:
    """
    Create contacts, contact groups, users for test purposes.

    Relationships:
        user_1: [contact_group_1, contact_group_2], [contact_1, contact_2, contact_3, contact_4]
        contact_group_1: [contact_1, contact_2]
        contact_group_2: [contact_1, contact_3]
        ---------------------------------------
        user_2: [], []
    """


@pytest.fixture
def get_non_existent_uuid() -> GET_NON_EXISTENT_UUID_RETURN_TYPE:
    """
    Returns valid, but non-existent for the given queryset UUID.

    This is a fixture, because of the need to access the database.
    """

    def _get_non_existent_uuid(queryset: QuerySet[Any]) -> UUID:
        random_uuid = uuid4()
        try:
            queryset.get(uuid=random_uuid)
        except queryset.model.DoesNotExist:
            return random_uuid
        else:
            return _get_non_existent_uuid(queryset)

    return _get_non_existent_uuid


@pytest.fixture
def non_existent_contact_uuid(get_non_existent_uuid: GET_NON_EXISTENT_UUID_RETURN_TYPE) -> UUID:
    return get_non_existent_uuid(Contact.objects.all())


@pytest.fixture
def non_existent_contact_group_uuid(get_non_existent_uuid: GET_NON_EXISTENT_UUID_RETURN_TYPE) -> UUID:
    return get_non_existent_uuid(ContactGroup.objects.all())


@pytest.fixture(scope="module")
def serialize_contact() -> SERIALIZE_CONTACT_RETURN_TYPE:
    """Serialize `Contact` instance to the expected response format of an API."""
    def _serialize_contact(contact: Contact) -> SERIALIZED_CONTACT:
        return OrderedDict(
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone_number=str(contact.phone_number),
            contact_groups=[contact_group.uuid for contact_group in contact.contact_groups.all()],
            uuid=str(contact.uuid),
        )

    return _serialize_contact


@pytest.fixture(scope="module")
def api_client() -> APIClient:
    api_client = APIClient()
    return api_client


class TestContactListView:

    @pytest.fixture(autouse=True)
    def _expose_fixtures(self, api_client: APIClient, serialize_contact: SERIALIZE_CONTACT_RETURN_TYPE) -> None:
        """
        Enables the use of `serialize_contact`, `api_client` fixtures in methods via instance attr.

        pytest doesn't allow this to be done in `__init__`
        """
        self._api_client = api_client
        self._contact_serializer = serialize_contact

    @pytest.fixture
    def contact_post_data_factory(self, contact_group_1) -> CONTACT_POST_DATA_FACTORY_RETURN_TYPE:
        """Return sample data for a 'POST /api/contacts' request, based on the given fields."""

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

    def test_get_is_not_accessible_by_anonymous_users(self):
        self._api_client.force_authenticate(user=None)
        response = self._api_client.get(CONTACT_LIST_ENDPOINT)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_for_authenticated_user(
        self,
        serialize_contact: SERIALIZE_CONTACT_RETURN_TYPE,
        user_1: User,
    ):
        """Test that 'GET /api/contacts' responds with 200 OK and a list of contacts for the authenticated user."""
        self._api_client.force_authenticate(user=user_1)
        response: Response = self._api_client.get(CONTACT_LIST_ENDPOINT)

        assert response.status_code == status.HTTP_200_OK
        self._assert_get_response_data_matches_users_contacts(response.data, user_1)

    def test_post_is_not_accessible_by_anonymous_users(
        self,
        contact_post_data_factory
    ):
        self._api_client.force_authenticate(user=None)
        response = self._api_client.post(CONTACT_LIST_ENDPOINT, data=contact_post_data_factory())
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
        contact_post_data_factory,
        user_1: User,
        exclude: tuple[str],
    ):
        """
        Check that 'POST /api/contacts' with a valid data responds with 201 CREATED and an accordingly serialized
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
    def test_post_insufficient_data_for_authenticated_user(
        self,
        contact_post_data_factory,
        user_1: User,
        exclude: tuple[str],
    ):
        """Check that 'POST /api/contacts' with an insufficient data responds with 400 BAD REQUEST."""
        data = contact_post_data_factory(exclude=exclude)
        self._assert_post_response_is_bad_request(data=data, user=user_1)

    @pytest.mark.parametrize(
        "contact_post_data_factory_kwargs", (
            {"email": "invalid_email"},
            {"phone_number": "invalid_phone_number"},
            {"contact_groups": ["invalid_contact_group_uuid"]},
        )
    )
    def test_post_invalid_data_for_authenticated_user(
        self,
        contact_post_data_factory,
        user_1: User,
        contact_post_data_factory_kwargs: POSTED_CONTACT,
    ):
        """Check that 'POST /api/contacts' with an invalid data responds with 400 BAD REQUEST."""
        data = contact_post_data_factory(**contact_post_data_factory_kwargs)
        self._assert_post_response_is_bad_request(data=data, user=user_1)

    def test_post_non_existent_uuid_for_authenticated_user(
        self,
        contact_post_data_factory,
        non_existent_contact_group_uuid: UUID,
        user_1: User,
    ):
        """A special case when given UUID is technically valid, but there is no contact group with such UUID."""
        contact_group_uuids = [str(non_existent_contact_group_uuid)]
        data = contact_post_data_factory(contact_groups=contact_group_uuids)
        self._assert_post_response_is_bad_request(data=data, user=user_1)

    def test_post_can_not_create_contact_within_not_owned_contact_group(
        self,
        contact_post_data_factory: CONTACT_POST_DATA_FACTORY_RETURN_TYPE,
        user_2: User,
        contact_group_1: ContactGroup,
    ):
        data = contact_post_data_factory(contact_groups=[str(contact_group_1.uuid)])
        self._assert_post_response_is_bad_request(data=data, user=user_2)

    def _assert_get_response_data_matches_users_contacts(
        self,
        get_response_data: SERIALIZED_CONTACT,
        user: User,
    ) -> None:
        """Check that ALL user's and ONLY user's contacts are present in the response"""
        user_contacts = user.contacts.all()
        assert len(get_response_data) == len(user_contacts)
        for contact in user_contacts:
            expected_contact_data = self._contact_serializer(contact)
            assert expected_contact_data in get_response_data

    def _assert_post_response_is_ok(
        self,
        data: POSTED_CONTACT,
        user: User | None = None,
    ) -> None:
        """
        Check that 'POST /api/contacts' responds with 201 CREATED and an accordingly serialized newly created contact
        instance.

        :param data: Data to be sent with the POST request
        :param user: `User` instance to authenticate under
        """
        self._api_client.force_authenticate(user=user)
        response = self._api_client.post(CONTACT_LIST_ENDPOINT, data=data)

        assert response.status_code == status.HTTP_201_CREATED
        response_data: SERIALIZED_CONTACT = response.data
        self._assert_post_data_matches_response_data(data, response_data)
        self._assert_post_response_data_is_saved_correctly(response_data, user)

    def _assert_post_response_is_bad_request(
        self,
        data: POSTED_CONTACT,
        user: User | None = None,
    ) -> None:
        """
        Check that 'POST /api/contacts' responds with 400 BAD REQUEST.

        :param data: Data to be sent with the POST request
        :param user: `User` instance to authenticate under
        """
        self._api_client.force_authenticate(user=user)
        response = self._api_client.post(CONTACT_LIST_ENDPOINT, data=data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(response.data)

    @staticmethod
    def _assert_post_data_matches_response_data(data: POSTED_CONTACT, response_data: SERIALIZED_CONTACT) -> None:
        """Check that data in the POST request to /api/contacts/ matches the data returned in response"""
        assert "uuid" in response_data
        data["contact_groups"] = [UUID(uuid_str) for uuid_str in data.get("contact_groups", [])]  # type: ignore
        for field, value in data.items():
            assert value == response_data[field]

    def _assert_post_response_data_is_saved_correctly(
        self,
        post_response_data: SERIALIZED_CONTACT,
        expected_user: User | None,
    ) -> None:
        """
        Check that the data returned in response to 'POST /api/contacts/' has been saved to the database correctly.

        :param expected_user: `User` instance under which the contact data was POSTed - to check it is saved to the DB
        """
        uuid = UUID(post_response_data["uuid"])  # type: ignore
        created_contact = Contact.objects.get(uuid=uuid)
        contact_expected_api_repr = self._contact_serializer(created_contact)
        assert contact_expected_api_repr == post_response_data
        assert created_contact.user == expected_user


class TestContactDetailView:

    @pytest.fixture(autouse=True)
    def _expose_fixtures(self, api_client: APIClient, serialize_contact: SERIALIZE_CONTACT_RETURN_TYPE) -> None:
        """
        Enables the use of `serialize_contact`, `api_client` fixtures in methods via instance attr.

        pytest doesn't allow this to be done in `__init__`
        """
        self._api_client = api_client
        self._contact_serializer = serialize_contact

    def test_get_is_not_accessible_by_anonymous_users(self, contact_1: Contact):
        self._api_client.force_authenticate(user=None)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=str(contact_1.uuid))
        response: Response = self._api_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_valid_uuid_for_authenticated_user(
        self,
        serialize_contact: SERIALIZE_CONTACT_RETURN_TYPE,
        user_1: User,
        contact_1: Contact,
    ):
        """Test that 'GET /api/contacts/<valid_uuid>/' responds with 200 OK and a contact for the authenticated user."""
        self._api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=str(contact_1.uuid))
        response: Response = self._api_client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK
        expected_contact_data = serialize_contact(contact_1)
        assert expected_contact_data == response.data

    def test_get_invalid_uuid_for_authenticated_user(
        self,
        serialize_contact: SERIALIZE_CONTACT_RETURN_TYPE,
        non_existent_contact_uuid: UUID,
        user_1: User,
        contact_1: Contact,
    ):
        """Test that 'GET /api/contacts/<invalid_uuid>/' responds with 404 NOT FOUND for the authenticated user."""
        self._api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=non_existent_contact_uuid)
        response: Response = self._api_client.get(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_is_not_accessible_by_anonymous_users(self, contact_1: Contact):
        self._api_client.force_authenticate(user=None)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=str(contact_1.uuid))
        response: Response = self._api_client.delete(endpoint)
        print(type(response))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_valid_uuid_for_authenticated_user(
        self,
        serialize_contact: SERIALIZE_CONTACT_RETURN_TYPE,
        user_1: User,
        contact_1: Contact,
    ):
        """Test that 'DELETE /api/contacts/<valid_uuid>/' responds with 204 NO CONTENT for the authenticated user."""
        self._api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=str(contact_1.uuid))
        response: Response = self._api_client.delete(endpoint)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_invalid_uuid_for_authenticated_user(
        self,
        serialize_contact: SERIALIZE_CONTACT_RETURN_TYPE,
        non_existent_contact_uuid: UUID,
        user_1: User,
        contact_1: Contact,
    ):
        """Test that 'DELETE /api/contacts/<invalid_uuid>/' responds with 404 NOT FOUND for the authenticated user."""
        self._api_client.force_authenticate(user=user_1)
        endpoint = CONTACT_DETAIL_ENDPOINT.format(uuid=non_existent_contact_uuid)
        response: Response = self._api_client.get(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND

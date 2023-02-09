import pytest

from address_book.contacts.models import Contact, ContactGroup
from address_book.users.models import User


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
    """User that has contact 5, and contact group 3."""
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
def contact_5(user_2: User) -> Contact:
    """Contact of `user_2`, belongs to `contact_group_3`."""
    return Contact.objects.create(
        first_name="first name 5",
        last_name="last name 5",
        email="contact_5@test.com",
        phone_number="+31555555555",
        user=user_2,
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


@pytest.fixture
def contact_group_3(user_2: User, contact_5: Contact) -> ContactGroup:
    """Contact group of `user_2`, contains `contact_5`."""
    contact_group = ContactGroup.objects.create(
        name="contact group 3",
        user=user_2,
    )
    contact_group.contacts.set([
        contact_5,
    ])
    return contact_group


@pytest.fixture(autouse=True)
def create_test_model_instances(
    contact_group_1: ContactGroup,
    contact_group_2: ContactGroup,
    contact_group_3: ContactGroup,
) -> None:
    """
    Create contacts, contact groups, users for test purposes.

    Relationships:
        user_1: [contact_group_1, contact_group_2], [contact_1, contact_2, contact_3, contact_4]
        contact_group_1: [contact_1, contact_2]
        contact_group_2: [contact_1, contact_3]
        ---------------------------------------
        user_2: [], []
    """

from django.urls import resolve, reverse

import pytest

from address_book.contacts.models import Contact, ContactGroup

pytestmark = pytest.mark.django_db

CONTACT_LIST_ENDPOINT = "/api/contacts/"
CONTACT_DETAIL_ENDPOINT = "/api/contacts/{uuid}/"
CONTACT_GROUP_LIST_ENDPOINT = "/api/contact_groups/"
CONTACT_GROUP_DETAIL_ENDPOINT = "/api/contact_groups/{uuid}/"
CONTACT_GROUP_CONTACT_LIST_ENDPOINT = "/api/contact_groups/{contact_group_uuid}/contacts/"
CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT = "/api/contact_groups/{contact_group_uuid}/contacts/{contact_uuid}/"
CONTACT_GROUP_SEARCH_ENDPOINT = "/api/contact_groups/search/"


def assert_view_name_matches_url(view_name: str, url: str, **kwargs):
    full_url = url.format(**kwargs)
    assert reverse(view_name, kwargs=kwargs) == full_url
    assert resolve(full_url).view_name == view_name


def test_contact_list():
    assert_view_name_matches_url("api:contact_list", CONTACT_LIST_ENDPOINT)


def test_contact_detail(contact_1: Contact):
    assert_view_name_matches_url("api:contact_detail", CONTACT_DETAIL_ENDPOINT, uuid=contact_1.uuid)


def test_contact_group_list():
    assert_view_name_matches_url("api:contact_group_list", CONTACT_GROUP_LIST_ENDPOINT)


def test_contact_group_detail(contact_group_1: ContactGroup):
    assert_view_name_matches_url("api:contact_group_detail", CONTACT_GROUP_DETAIL_ENDPOINT, uuid=contact_group_1.uuid)


def test_contact_group_contact_list(contact_group_1: ContactGroup):
    assert_view_name_matches_url(
        "api:contact_group_contact_list",
        CONTACT_GROUP_CONTACT_LIST_ENDPOINT,
        contact_group_uuid=contact_group_1.uuid,
    )


def test_contact_group_contact_detail(contact_1: Contact, contact_group_1: ContactGroup):
    assert_view_name_matches_url(
        "api:contact_group_contact_detail",
        CONTACT_GROUP_CONTACT_DETAIL_ENDPOINT,
        contact_group_uuid=contact_group_1.uuid,
        contact_uuid=contact_1.uuid,
    )


def test_contact_group_search():
    assert_view_name_matches_url("api:contact_group_search", CONTACT_GROUP_SEARCH_ENDPOINT)

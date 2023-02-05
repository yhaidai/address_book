from django.urls import path

from address_book.contacts.api.views import (
    ContactDetailView, ContactListView, ContactGroupDetailView, ContactGroupListView, ContactGroupContactListView,
    ContactGroupContactDetailView, ContactGroupSearch,
)

urlpatterns = [
    path("contacts/", ContactListView.as_view(), name="contact_list"),
    path("contacts/<uuid:uuid>", ContactDetailView.as_view(), name="contact_detail"),
    path("contact_groups/", ContactGroupListView.as_view(), name="contact_group_list"),
    path("contact_groups/<uuid:uuid>", ContactGroupDetailView.as_view(), name="contact_group_detail"),
    path(
        "contact_groups/<uuid:contact_group_uuid>/contacts",
        ContactGroupContactListView.as_view(),
        name="contact_group_contact_list",
    ),
    path(
        "contact_groups/<uuid:contact_group_uuid>/contacts/<uuid:contact_uuid>",
        ContactGroupContactDetailView.as_view(),
        name="contact_group_contact_detail",
    ),
    path("contact_groups/search", ContactGroupSearch.as_view(), name="contact_group_search")
]

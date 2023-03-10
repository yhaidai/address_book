from django.urls import path

from address_book.contacts.api.views import (
    ContactDetailView,
    ContactGroupAddListContactsView,
    ContactGroupDetailView,
    ContactGroupListView,
    ContactGroupRemoveContactView,
    ContactGroupSearchView,
    ContactListView,
)

urlpatterns = [
    path("contacts/", ContactListView.as_view(), name="contact_list"),
    path("contacts/<uuid:uuid>/", ContactDetailView.as_view(), name="contact_detail"),
    path("contact_groups/", ContactGroupListView.as_view(), name="contact_group_list"),
    path("contact_groups/<uuid:uuid>/", ContactGroupDetailView.as_view(), name="contact_group_detail"),
    path(
        "contact_groups/<uuid:contact_group_uuid>/contacts/",
        ContactGroupAddListContactsView.as_view(),
        name="contact_group_contact_list",
    ),
    path(
        "contact_groups/<uuid:contact_group_uuid>/contacts/<uuid:contact_uuid>/",
        ContactGroupRemoveContactView.as_view(),
        name="contact_group_contact_detail",
    ),
    path("contact_groups/search/", ContactGroupSearchView.as_view(), name="contact_group_search")
]

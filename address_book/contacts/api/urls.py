from django.urls import path

from address_book.contacts.api.views import (
    ContactDetailView, ContactListView, ContactGroupDetailView, ContactGroupListView,
)

urlpatterns = [
    path("contacts/", ContactListView.as_view(), name="contact_list"),
    path("contact/<uuid:uuid>", ContactDetailView.as_view(), name="contact_detail"),
    path("contact_groups/", ContactGroupListView.as_view(), name="contact_group_list"),
    path("contact_group/<uuid:uuid>", ContactGroupDetailView.as_view(), name="contact_group_detail"),
]

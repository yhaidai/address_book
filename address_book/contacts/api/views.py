from rest_framework.generics import RetrieveDestroyAPIView, ListCreateAPIView

from .serializers import ContactSerializer, ContactGroupSerializer
from ..models import Contact, ContactGroup


class ContactDetailView(RetrieveDestroyAPIView):
    """View for retrieving/deleting a particular contact by its UUID."""

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    lookup_field = "uuid"


class ContactListView(ListCreateAPIView):
    """View for listing contacts/creating a contact."""

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


class ContactGroupDetailView(RetrieveDestroyAPIView):
    """View for retrieving/deleting a particular contact group by its UUID."""

    queryset = ContactGroup.objects.all()
    serializer_class = ContactGroupSerializer
    lookup_field = "uuid"


class ContactGroupListView(ListCreateAPIView):
    """View for listing contact groups/creating a contact group."""

    queryset = ContactGroup.objects.all()
    serializer_class = ContactGroupSerializer

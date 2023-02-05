from uuid import UUID

from django.db.models import QuerySet, Manager
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from rest_framework import status
from rest_framework.generics import RetrieveDestroyAPIView, ListCreateAPIView, ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ContactSerializer, ContactGroupSerializer, ContactGroupContactSerializer
from ..models import Contact, ContactGroup


class ContactDetailView(RetrieveDestroyAPIView):
    """View for retrieving/deleting a particular contact by its UUID."""

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    lookup_field = "uuid"


class ContactListView(ListCreateAPIView):
    """View for listing contacts/creating a contact."""

    serializer_class = ContactSerializer

    def get_queryset(self) -> QuerySet[Contact]:
        """Filter contacts on the current user and prefetch related `contact_groups` to avoid N+1 problem."""
        user = self.request.user
        return Contact.objects.filter(user=user).prefetch_related("contact_groups")


class ContactGroupDetailView(RetrieveDestroyAPIView):
    """View for retrieving/deleting a particular contact group by its UUID."""

    queryset = ContactGroup.objects.all()
    serializer_class = ContactGroupSerializer
    lookup_field = "uuid"


class ContactGroupListView(ListCreateAPIView):
    """View for listing contact groups/creating a contact group."""

    serializer_class = ContactGroupSerializer

    def get_queryset(self) -> QuerySet[ContactGroup]:
        """Filter contact groups on the current user and prefetch related `contacts` to avoid N+1 problem."""
        user = self.request.user
        return ContactGroup.objects.filter(user=user).prefetch_related("contacts")


class ContactGroupRemoveContactView(APIView):
    """View for removing a contact from contact group by its UUID."""
    def delete(self, request: Request, contact_group_uuid: UUID, contact_uuid: UUID) -> Response:
        """
        Remove a contact from a group.

        :return: 404 NOT FOUND, error msg - if there is no contact/group with given UUID.
                 204 NO CONTENT - if the contact has been successfully removed from the group.
        """
        try:
            contact: Contact = Contact.objects.get(uuid=contact_uuid)
        except Contact.DoesNotExist:
            return Response(f"Contact with UUID '{contact_uuid}' does not exist", status=status.HTTP_404_NOT_FOUND)

        try:
            contact_group: ContactGroup = ContactGroup.objects.get(uuid=contact_group_uuid)
        except ContactGroup.DoesNotExist:
            return Response(
                f"ContactGroup with UUID '{contact_group_uuid}' does not exist", status=status.HTTP_404_NOT_FOUND,
            )

        contact_group.contacts.remove(contact)
        return Response("", status=status.HTTP_204_NO_CONTENT)


class ContactGroupAddListContactsView(ListCreateAPIView):
    """View for adding existing contact to a group and listing all contacts within the group."""

    serializer_class = ContactGroupContactSerializer

    def get_queryset(self) -> QuerySet[Contact]:
        """
        Filter contacts on the current user and contact group and prefetch related `contact_groups` to avoid N+1
        problem.

        :raise Http404: if there is no contact group with given UUID
        """
        user = self.request.user
        contact_group_uuid = self.kwargs["contact_group_uuid"]

        try:
            contact_group: ContactGroup = ContactGroup.objects.get(user=user, uuid=contact_group_uuid)
        except ContactGroup.DoesNotExist as error:
            raise Http404(f"ContactGroup with UUID '{contact_group_uuid}' does not exist") from error

        return contact_group.contacts.prefetch_related("contact_groups")

    def create(self, request: Request, contact_group_uuid: UUID) -> Response:
        """
        Add an existing contact to the contact group.

        :return Response: 404 NOT FOUND, error msg - if there is no contact/group with given UUID
                          303 SEE OTHER, serialized contact - if this contact is already in the group
                          200 OK, serialized contact - if the contact has been successfully added to the group
        """
        contact_uuid = request.data["uuid"]
        try:
            contact: Contact = Contact.objects.get(uuid=contact_uuid)
        except Contact.DoesNotExist:
            return Response(f"Contact with UUID '{contact_uuid}' does not exist", status=status.HTTP_404_NOT_FOUND)

        try:
            contact_group: ContactGroup = ContactGroup.objects.get(uuid=contact_group_uuid)
        except ContactGroup.DoesNotExist:
            return Response(
                f"ContactGroup with UUID '{contact_group_uuid}' does not exist", status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ContactGroupContactSerializer(contact, context={"request": request})

        if contact in contact_group.contacts.all():
            return Response(serializer.data, status=status.HTTP_303_SEE_OTHER)

        contact_group.contacts.add(contact)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(name="name", location=OpenApiParameter.QUERY, description="Name of the contact group"),
        ],
    )
)
class ContactGroupSearch(ListAPIView):
    """View for searching contact groups by name."""

    serializer_class = ContactGroupSerializer

    def get_queryset(self) -> QuerySet[ContactGroup]:
        """
        Search contact groups for the current user by name (case-insensitive).

        If `name` query parameter is empty - return all contact groups for the current user.
        """
        user = self.request.user
        name_query = self.request.query_params.get("name", "")
        return ContactGroup.objects.filter(user=user, name__icontains=name_query).prefetch_related("contacts")

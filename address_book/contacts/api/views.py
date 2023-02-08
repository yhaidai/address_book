from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.http import Http404

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import status
from rest_framework.fields import UUIDField
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Contact, ContactGroup
from .mixins import CreateViewMixin, DestroyViewMixin, ListViewMixin, RetrieveViewMixin
from .schema_utils import (
    CONTACT_GROUP_NOT_FOUND_RESPONSE,
    CONTACT_GROUP_RESPONSE,
    CONTACT_NOT_FOUND_RESPONSE,
    CONTACT_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from .serializers import ContactGroupSerializer, ContactSerializer


class ContactView(GenericAPIView):

    serializer_class = ContactSerializer

    def get_queryset(self) -> QuerySet[Contact]:
        """Filter contacts on the current user and prefetch related `contact_groups` to avoid N+1 problem."""
        user = self.request.user
        return Contact.objects.filter(user=user).prefetch_related("contact_groups")  # type: ignore


class ContactGroupView(GenericAPIView):

    serializer_class = ContactGroupSerializer

    def get_queryset(self) -> QuerySet[ContactGroup]:
        """Filter contact groups on the current user and prefetch related `contacts` to avoid N+1 problem."""
        user = self.request.user
        return ContactGroup.objects.filter(user=user).prefetch_related("contacts")  # type: ignore


@extend_schema_view(
    get=extend_schema(
        responses={
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_200_OK: ContactSerializer,
        },
        examples=[
            NOT_FOUND_RESPONSE,
            CONTACT_RESPONSE,
        ],
    ),
    delete=extend_schema(
        responses={
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_204_NO_CONTENT: None,
        },
        examples=[
            NOT_FOUND_RESPONSE,
        ],
    ),
)
class ContactDetailView(ContactView, RetrieveViewMixin, DestroyViewMixin):
    """View for retrieving/deleting a particular contact by its UUID."""

    lookup_field = "uuid"


@extend_schema_view(
    get=extend_schema(
        examples=[
            CONTACT_RESPONSE,
        ],
    ),
    post=extend_schema(
        examples=[
            CONTACT_RESPONSE,
        ],
    )
)
class ContactListView(ContactView, ListViewMixin, CreateViewMixin):
    """View for listing contacts/creating a contact."""


@extend_schema_view(
    get=extend_schema(
        responses={
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_200_OK: ContactGroupSerializer,
        },
        examples=[
            NOT_FOUND_RESPONSE,
            CONTACT_GROUP_RESPONSE,
        ],
    ),
    delete=extend_schema(
        responses={
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_204_NO_CONTENT: None,
        },
        examples=[
            NOT_FOUND_RESPONSE,
        ],
    ),
)
class ContactGroupDetailView(ContactGroupView, RetrieveViewMixin, DestroyViewMixin):
    """View for retrieving/deleting a particular contact group by its UUID."""

    lookup_field = "uuid"


@extend_schema_view(
    get=extend_schema(
        examples=[
            CONTACT_GROUP_RESPONSE,
        ],
    ),
    post=extend_schema(
        examples=[
            CONTACT_GROUP_RESPONSE,
        ],
    )
)
class ContactGroupListView(ContactGroupView, ListViewMixin, CreateViewMixin):
    """View for listing contact groups/creating a contact group."""


@extend_schema_view(
    delete=extend_schema(
        responses={
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_204_NO_CONTENT: None,
        },
        examples=[
            CONTACT_NOT_FOUND_RESPONSE,
            CONTACT_GROUP_NOT_FOUND_RESPONSE,
        ],
    ),
)
class ContactGroupRemoveContactView(APIView):
    """View for removing a contact from contact group by its UUID."""
    def delete(self, request: Request, contact_group_uuid: UUID, contact_uuid: UUID) -> Response:
        """
        Remove a contact from a group.

        :return: 404 NOT FOUND, error msg - if there is no contact/group with given UUID.
                 204 NO CONTENT - if the contact has been successfully removed from the group.
        """
        user = self.request.user

        try:
            contact: Contact = Contact.objects.get(uuid=contact_uuid, user=user)  # type: ignore
        except Contact.DoesNotExist:
            return Response(
                {"detail": f"Contact with UUID '{contact_uuid}' does not exist for your user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            contact_group: ContactGroup = ContactGroup.objects.get(uuid=contact_group_uuid, user=user)  # type: ignore
        except ContactGroup.DoesNotExist:
            return Response(
                {"detail": f"ContactGroup with UUID '{contact_group_uuid}' does not exist for your user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        contact_group.contacts.remove(contact)
        return Response("", status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(
        responses={
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_200_OK: ContactSerializer,
        },
        examples=[
            NOT_FOUND_RESPONSE,
            CONTACT_RESPONSE,
        ],
    ),
    post=extend_schema(
        request=inline_serializer(name="Contact UUID", fields={"uuid": UUIDField()}),
        responses={
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_200_OK: ContactSerializer,
            status.HTTP_303_SEE_OTHER: OpenApiTypes.OBJECT,
        },
        examples=[
            CONTACT_NOT_FOUND_RESPONSE,
            CONTACT_GROUP_NOT_FOUND_RESPONSE,
            CONTACT_RESPONSE,
        ],
    ),
)
class ContactGroupAddListContactsView(ListCreateAPIView):
    """View for adding existing contact to a group and listing all contacts within the group."""

    serializer_class = ContactSerializer

    def get_queryset(self) -> QuerySet[Contact]:
        """
        Filter contacts on the current user and contact group and prefetch related `contact_groups` to avoid N+1
        problem.

        :raise Http404: if there is no contact group with given UUID
        """
        user = self.request.user
        contact_group_uuid: UUID = self.kwargs["contact_group_uuid"]

        try:
            contact_group: ContactGroup = ContactGroup.objects.get(user=user, uuid=contact_group_uuid)  # type: ignore
        except ContactGroup.DoesNotExist as error:
            raise Http404(f"ContactGroup with UUID '{contact_group_uuid}' does not exist for your user.") from error

        return contact_group.contacts.prefetch_related("contact_groups")

    def create(self, request: Request,  *args: Any, **kwargs: Any) -> Response:
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
            return Response(
                {"detail": f"Contact with UUID '{contact_uuid}' does not exist for your user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        contact_group_uuid: UUID = self.kwargs["contact_group_uuid"]
        try:
            contact_group: ContactGroup = ContactGroup.objects.get(uuid=contact_group_uuid)
        except ContactGroup.DoesNotExist:
            return Response(
                {"detail": f"ContactGroup with UUID '{contact_group_uuid}' does not exist for your user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ContactSerializer(contact, context={"request": request})

        if contact in contact_group.contacts.all():
            return Response(serializer.data, status=status.HTTP_303_SEE_OTHER)

        contact_group.contacts.add(contact)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(name="name", location=OpenApiParameter.QUERY, description="Name of the contact group"),
        ],
        examples=[
            CONTACT_GROUP_RESPONSE,
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
        return ContactGroup.objects.filter(
            user=user, name__icontains=name_query,
        ).prefetch_related("contacts")  # type: ignore

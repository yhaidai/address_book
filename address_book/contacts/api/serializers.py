from rest_framework import serializers

from ..models import Contact, ContactGroup
from .validators import (
    ContactGroupsBelongToContactCreatorValidator,
    NonEmptyTogetherValidator,
)


class ContactSerializer(serializers.ModelSerializer):
    """
    Serializer class for contacts.

    User field is automatically set to current user (based on request context) during deserialization.
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    contact_groups = serializers.SlugRelatedField(
        queryset=ContactGroup.objects.all(), slug_field="uuid", many=True, required=False,
    )

    class Meta:
        model = Contact
        fields = ("first_name", "last_name", "email", "phone_number", "contact_groups", "user", "uuid",)
        validators = (
            NonEmptyTogetherValidator(("first_name", "last_name")),
            NonEmptyTogetherValidator(("email", "phone_number")),
            ContactGroupsBelongToContactCreatorValidator()
        )


class ContactGroupSerializer(serializers.ModelSerializer):
    """
    Serializer class for contact groups.

    User field is automatically set to current user (based on request context) during deserialization.
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    contacts = serializers.SlugRelatedField(
        queryset=Contact.objects.all(), slug_field="uuid", many=True, required=False,
    )

    class Meta:
        model = ContactGroup
        fields = ("name", "contacts", "user", "uuid",)

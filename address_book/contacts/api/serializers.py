from rest_framework import serializers

from ..models import Contact, ContactGroup


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


class ContactGroupContactSerializer(ContactSerializer):
    """
    Serializer class for contacts within contact groups; used for correct automatic schema generation.

    Similar to `ContactSerializer`, but all fields are read-only, except for the write-only UUID field.
    """

    uuid = serializers.UUIDField(write_only=True)
    contact_groups = serializers.SlugRelatedField(slug_field="uuid", many=True, read_only=True)

    class Meta(ContactSerializer.Meta):
        read_only_fields = ("first_name", "last_name", "email", "phone_number",)

from rest_framework import serializers

from ..models import Contact, ContactGroup


class ContactSerializer(serializers.HyperlinkedModelSerializer):
    """
    Hyperlinked (de)serializer class for contacts.

    User field is automatically set to current user (based on request context) during deserialization.
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Contact
        fields = ("first_name", "last_name", "email", "phone_number", "url", "contact_groups", "user",)
        extra_kwargs = {
            "url": {"view_name": "api:contact_detail", "lookup_field": "uuid"},
            "contact_groups": {"view_name": "api:contact_group_detail", "lookup_field": "uuid"},
        }


class ContactGroupSerializer(serializers.HyperlinkedModelSerializer):
    """
    Hyperlinked (de)serializer class for contact groups.

    User field is automatically set to current user (based on request context) during deserialization.
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = ContactGroup
        fields = ("name", "url", "contacts", "user",)
        extra_kwargs = {
            "url": {"view_name": "api:contact_detail", "lookup_field": "uuid"},
            "contacts": {"view_name": "api:contact_detail", "lookup_field": "uuid"},
        }

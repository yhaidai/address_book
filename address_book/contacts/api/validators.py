from typing import Iterable

from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from address_book.contacts.models import ContactGroup
from address_book.users.models import User


class NonEmptyTogetherValidator:

    _MESSAGE = _("At least one of the fields {field_names} mustn't be empty.")

    def __init__(self, fields: Iterable[str], message=None):
        self._fields = fields
        self._message = message or self._MESSAGE

    def __call__(self, attrs):
        if not any(attrs.get(field) for field in self._fields):
            field_names = ", ".join(self._fields)
            raise ValidationError(self._message.format(field_names=field_names))


class ContactGroupsBelongToContactCreatorValidator:
    """Validate that all contact groups belong to the same user that the contact belongs to."""

    _MESSAGE = _("Provided contact group UUID(s) do not exist for your user.")

    def __init__(self, message=None):
        self._message = message or self._MESSAGE

    def __call__(self, attrs):
        expected_user: User = attrs["user"]
        contact_groups: list[ContactGroup] = attrs["contact_groups"]

        if any(contact_group.user != expected_user for contact_group in contact_groups):
            raise ValidationError(str(self._message))

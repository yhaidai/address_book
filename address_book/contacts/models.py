import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CASCADE

from phonenumber_field.modelfields import PhoneNumberField

User = get_user_model()


class UUIDModel(models.Model):
    """ABC for models which have autogenerated UUID field."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True


class Contact(UUIDModel):
    """Contacts have many-to-one relationship with users and many-to-many with contact groups."""

    user = models.ForeignKey(User, on_delete=CASCADE, related_name="contacts", related_query_name="contact")
    first_name = models.CharField(max_length=63)
    last_name = models.CharField(max_length=63)
    email = models.EmailField(max_length=255)
    phone_number = PhoneNumberField(max_length=15)


class ContactGroup(UUIDModel):
    """
    Contact groups have many-to-one relationship with users and many-to-many with contacts.

    Relationship with users may seem redundant, given that both contacts within the group and the group itself would
    have the same user. However, this is still necessary to be able to create empty groups (with no contacts).
    """

    user = models.ForeignKey(User, on_delete=CASCADE, related_name="contact_groups", related_query_name="contact_group")
    contacts = models.ManyToManyField(Contact, related_name="contact_groups", related_query_name="contact_group")
    name = models.CharField(max_length=255)
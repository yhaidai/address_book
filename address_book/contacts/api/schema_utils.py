import uuid

from drf_spectacular.utils import OpenApiExample
from rest_framework import status

NOT_FOUND_RESPONSE = OpenApiExample(
    "Not Found",
    value={"detail": "Not found."},
    response_only=True,
    status_codes=[status.HTTP_404_NOT_FOUND],
)

CONTACT_NOT_FOUND_RESPONSE = OpenApiExample(
    "Contact Not Found",
    value={"detail": f"Contact with UUID '{uuid.uuid4()}' does not exist."},

    response_only=True,
    status_codes=[status.HTTP_404_NOT_FOUND],
)

CONTACT_GROUP_NOT_FOUND_RESPONSE = OpenApiExample(
    "Contact Group Not Found",
    value={"detail": f"ContactGroup with UUID '{uuid.uuid4()}' does not exist."},
    response_only=True,
    status_codes=[status.HTTP_404_NOT_FOUND],
)

CONTACT_RESPONSE = OpenApiExample(
    "Contact",
    value={
        "first_name": "string",
        "last_name": "string",
        "email": "user@example.com",
        "phone_number": "+31123456789",
        "contact_groups": [
            uuid.uuid4(),
            uuid.uuid4(),
        ]
    },
    response_only=True,
    status_codes=[status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_303_SEE_OTHER],
)

CONTACT_GROUP_RESPONSE = OpenApiExample(
    "Contact Group",
    value={
        "name": "string",
        "uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "contacts": [
            uuid.uuid4(),
            uuid.uuid4(),
        ],
    },
    response_only=True,
    status_codes=[status.HTTP_200_OK, status.HTTP_201_CREATED],
)

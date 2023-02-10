import functools
from itertools import chain, combinations
from typing import Any, Callable, Iterable, TypeAlias, TypeVar

from django.apps import apps
from django.db.models import ForeignObjectRel, Model
from django.urls import resolve, reverse

import pytest

from address_book.users.models import User
from address_book.users.tests.factories import UserFactory

T = TypeVar("T")
SERIALIZED_QUERYSET: TypeAlias = tuple[dict[str, Any], ...]


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory()


def powerset(iterable: Iterable[T]) -> chain[tuple[T, ...]]:
    """powerset([1, 2, 3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def serialize_queryset(model_class: type[Model]) -> SERIALIZED_QUERYSET:
    """
    Serialize queryset for a given model class, including fields evaluation.

    Used to make the comparison of otherwise LAZY querysets in `assert_database_state_unchanged` trivial.
    Excludes fields for backward relationships - such relationships will be traversed anyway in a forward manner.
    """
    queryset = model_class.objects.all()
    result = tuple(
        {
            field.name: field.value_from_object(obj)  # type: ignore
            for field in model_class._meta.get_fields()
            if not isinstance(field, ForeignObjectRel)  # Skip fields for backward relationships
        }
        for obj in queryset
    )
    return result


def get_serialized_model_querysets() -> tuple[SERIALIZED_QUERYSET, ...]:
    """Return serialized querysets for all models."""
    return tuple(serialize_queryset(model_class) for model_class in apps.get_models())


def assert_database_state_unchanged(func: Callable):
    """Decorator for tests to ensure that the state of the database remains the same at the end of test execution."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        initial_querysets = get_serialized_model_querysets()

        result = func(*args, **kwargs)

        eventual_querysets = get_serialized_model_querysets()
        for initial_queryset, eventual_queryset in zip(initial_querysets, eventual_querysets):
            assert initial_queryset == eventual_queryset

        return result

    return wrapper


def assert_view_name_matches_url(view_name: str, url: str, **kwargs):
    full_url = url.format(**kwargs)
    assert reverse(view_name, kwargs=kwargs) == full_url
    assert resolve(full_url).view_name == view_name

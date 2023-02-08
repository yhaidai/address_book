from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)


class CreateViewMixin(CreateModelMixin):
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class ListViewMixin(ListModelMixin):
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RetrieveViewMixin(RetrieveModelMixin):
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class DestroyViewMixin(DestroyModelMixin):
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

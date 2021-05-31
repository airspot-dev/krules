import typing
from django.http import HttpRequest
from rest_framework import permissions
from django.conf import settings


class SimpleApiKeyPermissionClass(permissions.BasePermission):
    """
    This is an abstract class ment to be used in a typcal krules environment
    where the api key is provided in a configuration provider, then
    injected in django settings.
    The configuration value could be expressed as a list to facilitate the transition
    to a new value without interrupting the operation of the client services
    which receive the same configuration but potentially not at the exact same moment
    The client uses the first element of the list
    """

    settings_key: typing.Union[str, typing.List] = None

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:

        assert self.settings_key is not None, (
            f"{self.__class__.__name__} must define a settings_key attribute"
        )

        # get key from authorization header
        authorization = request.META.get("HTTP_AUTHORIZATION")

        if not authorization:
            return False

        try:
            _, key = authorization.split("Api-Key ")
        except ValueError:
            return False

        value = getattr(settings, self.settings_key)
        if isinstance(value, typing.List):
            return key in getattr(settings, self.settings_key)
        return key == value

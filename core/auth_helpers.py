from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import authentication_classes

INTERNAL_AUTH_CLASSES = [SessionAuthentication, TokenAuthentication]
internal_auth = authentication_classes(INTERNAL_AUTH_CLASSES)


class InternalAPIAuthMixin:
    """InternalAPIAuthMixin."""

    authentication_classes = INTERNAL_AUTH_CLASSES

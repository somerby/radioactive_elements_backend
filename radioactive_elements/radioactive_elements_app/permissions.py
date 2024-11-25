from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions, authentication, exceptions
from .models import CustomUser
from .redis import session_storage

class AuthBySSID(authentication.BaseAuthentication):
    def authenticate(self, request):
        ssid = request.COOKIES.get('session_id')
        if ssid is None:
            return AnonymousUser(), None
        try:
            email = session_storage.get(ssid).decode("utf-8")
        except Exception as e:
            return AnonymousUser(), None
        user = CustomUser.objects.filter(email=email).first()
        if user is None:
            return AnonymousUser(), None
        return user, None

class IsAuth(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return bool(request.user.is_staff or request.user.is_superuser)
        return False

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return bool(request.user.is_superuser)
        return False
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == "admin"


class IsCaixaOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in {"caixa", "admin"}

from dataclasses import dataclass

from django.core import signing
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


TOKEN_SALT = "movimentacao.api"
TOKEN_MAX_AGE = 60 * 60  # one hour


@dataclass
class SignedTokenUser:
    subject: str
    role: str

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


def create_access_token(subject, role):
    return signing.dumps(
        {"sub": str(subject), "role": role},
        salt=TOKEN_SALT,
    )


class SignedTokenAuthentication(BaseAuthentication):
    """Authenticate short-lived bearer tokens issued by the application logins."""

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return None
        if not header.startswith("Bearer "):
            raise AuthenticationFailed("Credencial inválida.")

        try:
            payload = signing.loads(
                header[7:].strip(), salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE
            )
        except (signing.BadSignature, signing.SignatureExpired, ValueError, TypeError):
            raise AuthenticationFailed("Credencial inválida ou expirada.")

        if not payload.get("sub") or payload.get("role") not in {"admin", "caixa"}:
            raise AuthenticationFailed("Credencial inválida.")
        return SignedTokenUser(payload["sub"], payload["role"]), header[7:].strip()

    def authenticate_header(self, request):
        return "Bearer"

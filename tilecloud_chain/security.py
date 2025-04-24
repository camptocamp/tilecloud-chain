"""Security policy for the pyramid application."""

import os

import c2cwsgiutils.auth
import pyramid.request
from c2cwsgiutils.auth import AuthConfig
from pyramid.security import Allowed, Denied


class User:
    """The user definition."""

    login: str | None
    name: str | None
    url: str | None
    is_auth: bool
    token: str | None
    is_admin: bool
    request: pyramid.request.Request

    def __init__(
        self,
        auth_type: str,
        login: str | None,
        name: str | None,
        url: str | None,
        is_auth: bool,
        token: str | None,
        request: pyramid.request.Request,
    ) -> None:
        self.auth_type = auth_type
        self.login = login
        self.name = name
        self.url = url
        self.is_auth = is_auth
        self.token = token
        self.request = request
        self.is_admin = c2cwsgiutils.auth.check_access(self.request)

    def has_access(self, auth_config: AuthConfig) -> bool:
        """Check if the user has access to the tenant."""
        if self.is_admin:
            return True
        if "github_repository" in auth_config:
            return c2cwsgiutils.auth.check_access_config(self.request, auth_config)

        return False


class SecurityPolicy:
    """The pyramid security policy."""

    def identity(self, request: pyramid.request.Request) -> User:
        """Return app-specific user object."""
        if not hasattr(request, "user"):
            if "TEST_USER" in os.environ:
                user = User(
                    auth_type="test_user",
                    login=os.environ["TEST_USER"],
                    name=os.environ["TEST_USER"],
                    url="https://example.com/user",
                    is_auth=True,
                    token=None,
                    request=request,
                )
            else:
                is_auth, c2cuser = c2cwsgiutils.auth.is_auth_user(request)
                user = User(
                    "github_oauth",
                    c2cuser.get("login"),
                    c2cuser.get("name"),
                    c2cuser.get("url"),
                    is_auth,
                    c2cuser.get("token"),
                    request,
                )
            request.user = user
        return request.user  # type: ignore[no-any-return]

    def authenticated_userid(self, request: pyramid.request.Request) -> str | None:
        """Return a string ID for the user."""
        identity = self.identity(request)

        if identity is None:
            return None

        return identity.login

    def permits(
        self,
        request: pyramid.request.Request,
        context: AuthConfig,
        permission: str,
    ) -> Allowed | Denied:
        """Allow access to everything if signed in."""
        identity = self.identity(request)

        if identity is None:
            return Denied("User is not signed in.")
        if identity.auth_type in ("test_user",):
            return Allowed(f"All access auth type: {identity.auth_type}")
        if identity.is_admin:
            return Allowed("The User is admin.")
        if permission == "all":
            return Denied("Root access is required.")
        if identity.has_access(context):
            return Allowed("The User has access.")
        return Denied(f"The User has no access to source {permission}.")

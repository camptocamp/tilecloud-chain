"""Security policy for the application."""

import c2cwsgiutils.auth
import pyramid.request
from c2cwsgiutils.auth import AuthConfig


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

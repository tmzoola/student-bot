from core.config import settings
from fastapi import Response
from starlette.requests import Request
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed


class AdminAuth(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> AdminUser | None:
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session.update({"username": username})
            return response
        raise LoginFailed("Invalid username or password")

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response

    async def is_authenticated(self, request: Request) -> bool:
        return "username" in request.session

    def get_admin_user(self, request: Request) -> AdminUser | None:
        username = request.session.get("username")
        return AdminUser(username=username) if username else None

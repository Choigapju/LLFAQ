from sqladmin import ModelView
from database.models import FAQModel, NoticeModel
from sqladmin.authentication import AuthenticationBackend
from fastapi import Request

class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str):
        super().__init__(secret_key=secret_key)

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username == "itlab" and password == "likelion":
            request.session.update({"token": "admin"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token or token != "admin":
            return False
        return True

class FAQAdmin(ModelView, model=FAQModel):  # FAQ -> FAQModel로 변경
    column_list = ["id", "keywords", "question", "answer"]
    column_searchable_list = ["keywords", "question"]
    can_create = True
    can_edit = True
    can_delete = True
    name = "FAQ"
    name_plural = "FAQs"

class NoticeAdmin(ModelView, model=NoticeModel):  # Notice -> NoticeModel로 변경
    column_list = ["id", "title", "content", "created_at"]
    column_searchable_list = ["title", "content"]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Notice"
    name_plural = "Notices"
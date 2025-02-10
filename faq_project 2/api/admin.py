from sqladmin import ModelView
from database.models import UserModel
from sqladmin.authentication import AuthenticationBackend
from fastapi import Request
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        
        # 관리자 계정 인증 (프로덕션에서는 데이터베이스 확인)
        if username == "itlab" and password == "likelion":  # 상황에 맞춰 변경 필요
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

class UserAdmin(ModelView, model=UserModel):
    column_list = [
        "id", "username", "email", "is_admin", 
        "can_edit", "created_at"
    ]
    column_searchable_list = ["username", "email"]
    column_sortable_list = ["id", "username", "created_at"]
    column_details_exclude_list = ["password_hash"]
    can_create = True
    can_edit = True
    can_delete = True
    name = "User"
    name_plural = "Users"
    
    async def on_model_change(self, data: dict, model: UserModel, is_created: bool):
        """사용자 생성/수정 시 비밀번호 해싱"""
        if "password" in data:
            model.password_hash = pwd_context.hash(data["password"])
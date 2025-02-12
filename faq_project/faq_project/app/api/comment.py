from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreate, Comment as CommentSchema, CommentUpdate
from app.core.security import get_current_user, get_current_admin_user

router = APIRouter()

@router.post("/", response_model=CommentSchema)
async def create_comment(
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """댓글 작성"""
    db_comment = Comment(
        content=comment.content,
        user_id=current_user.id,
        faq_id=comment.faq_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("/faq/{faq_id}", response_model=List[CommentSchema])
async def read_comments(
    faq_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """FAQ의 댓글 목록 조회"""
    comments = db.query(Comment)\
        .filter(Comment.faq_id == faq_id, Comment.is_deleted == False)\
        .offset(skip)\
        .limit(limit)\
        .all()
    return comments

@router.put("/{comment_id}", response_model=CommentSchema)
async def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """댓글 수정 (작성자 또는 관리자만 가능)"""
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if db_comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_comment.content = comment_update.content
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """댓글 삭제 (작성자 또는 관리자만 가능)"""
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if db_comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_comment.is_deleted = True
    db.commit()
    return {"message": "Comment deleted successfully"}
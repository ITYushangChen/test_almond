"""
Data models for the application.
Since we're using Supabase client, we don't need SQLAlchemy models.
These are just for reference and type hints.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash

@dataclass
class User:
    """User model for local authentication"""
    id: Optional[int] = None
    username: str = ''
    password_hash: str = ''
    created_at: Optional[datetime] = None
    
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class Post:
    """Post model - maps to Supabase posts table"""
    id: Optional[int] = None
    content: str = ''
    language: Optional[str] = None
    base_theme: Optional[str] = None
    sub_theme: Optional[str] = None
    sentiment: Optional[str] = None
    likes: int = 0
    num_comments: int = 0
    created_at: Optional[datetime] = None

@dataclass  
class Comment:
    """Comment model - maps to Supabase comments table"""
    id: Optional[int] = None
    post_id: Optional[int] = None
    content: str = ''
    language: Optional[str] = None
    base_theme: Optional[str] = None
    sub_theme: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: Optional[datetime] = None

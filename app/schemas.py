from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: str
    email: str
    nickname: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginIn(BaseModel):
    email: EmailStr
    nickname: str = Field(min_length=1, max_length=120)


class LoginOut(BaseModel):
    token: str
    user: UserOut


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant|system|tool)$")
    content: str
    client_message_id: str | None = Field(default=None, max_length=120)


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    status: str
    client_message_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatStreamIn(BaseModel):
    conversation_id: str | None = None
    content: str = Field(min_length=1)
    client_message_id: str = Field(min_length=1, max_length=120)
    search_mode: str = Field(default="off", pattern="^(off|auto|force)$")


class SearchIn(BaseModel):
    query: str = Field(min_length=1)
    mode: str = Field(default="force", pattern="^(off|auto|force)$")
    conversation_id: str | None = None


class SearchResultOut(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    published_at: str | None = None


class SearchOut(BaseModel):
    provider: str
    status: str
    results: list[SearchResultOut]

 

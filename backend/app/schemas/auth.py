from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: int
    username: str

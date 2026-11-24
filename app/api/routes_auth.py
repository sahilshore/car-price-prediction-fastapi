from fastapi import APIRouter
from pydantic import BaseModel
from app.core.security import create_token

router = APIRouter()

class AuthInput(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(auth: AuthInput):
    # Replace these with your actual authentication logic
    if (auth.username == "admin") and (auth.password == "admin"):
        token = create_token({"sub": auth.username})
        return {"access_token": token}
    else:
        return {"error": "Invalid username or password"}

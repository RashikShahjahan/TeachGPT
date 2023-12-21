from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from utils import  get_single_story, write_story_to_mongodb
import uvicorn
from pydantic import BaseModel
from pymongo import MongoClient
import secrets
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

# Set up CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://banglallm.rashik.sh"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# to be used for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key to encode and decode JWT tokens
SECRET_KEY = "9a8b7c6d5e4f3g2h1i0j"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class StoryRequest(BaseModel):
    story: str

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    password: str
    inviteCode: str  # New field for invite code



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

client = MongoClient('mongodb://localhost:27017/')
db = client['stories']
users_collection = db['users']



invite_codes_collection = db['invite_codes']  # New collection for invite codes

def generate_invite_code():
    return secrets.token_urlsafe(16)  # Generates a 16-character URL-safe token


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(username: str):
    user_dict = users_collection.find_one({"username": username})
    if user_dict:
        return UserInDB(**user_dict)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/generate_invite_code")
async def generate_invite_code_endpoint():
    invite_code = generate_invite_code()
    invite_codes_collection.insert_one({"code": invite_code, "used": False})
    return {"invite_code": invite_code}

@app.post("token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=400, detail="Invalid token")
        token_data = User(username=username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = get_user(token_data.username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.post("register")
async def register(user_create: UserCreate):
    # Check if the invite code is valid and not used
    invite_code_record = invite_codes_collection.find_one({"code": user_create.inviteCode, "used": False})
    if not invite_code_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired invite code"
        )

    # Mark the invite code as used
    invite_codes_collection.update_one({"_id": invite_code_record["_id"]}, {"$set": {"used": True}})

    hashed_password = get_password_hash(user_create.password)
    user = {"username": user_create.username, "hashed_password": hashed_password}
    result = users_collection.insert_one(user)
    return {"username": user_create.username}


@app.get("draft")
async def get_draft():
    draft = get_single_story()
    if draft:
        return {"draft":draft}
    else:
        return {"draft":"No drafts to edit!"}


@app.post("draft")
async def publish_draft(story_request: StoryRequest, current_user: UserInDB = Depends(get_current_user)):
    story_id = str(write_story_to_mongodb(story_request.story))
    return {"story_id":story_id}

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        #ssl_certfile="/home/ec2-user/securefolder/fullchain.pem",  # Certificate file
        #ssl_keyfile="/home/ec2-user/securefolder/privkey.pem"      # Private key file
    )

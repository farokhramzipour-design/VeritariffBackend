
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as req

from app import crud, schemas
from app.api import deps
from app.core.config import settings

router = APIRouter()

@router.get("/login/google/authorize")
def login_google_authorize():
    """
    Redirect the user to the Google login page.
    """
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={settings.GOOGLE_REDIRECT_URI}&scope=openid%20email%20profile&access_type=offline"
    )

@router.get("/login/google/callback", response_model=schemas.User)
def login_google_callback(
    code: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Callback for Google login.
    """
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = req.post(token_url, data=data)
    access_token = response.json().get("access_token")
    id_token_str = response.json().get("id_token")
    
    try:
        id_info = id_token.verify_oauth2_token(id_token_str, requests.Request(), settings.GOOGLE_CLIENT_ID)
        
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        google_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name')
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    user = crud.user.get_by_google_id(db, google_id=google_id)
    if not user:
        user = crud.user.get_by_email(db, email=email)
        if user:
            # Link existing user with Google ID
            user = crud.user.update(db, db_obj=user, obj_in={"google_id": google_id})
        else:
            # Create new user
            user_in = schemas.UserCreate(email=email, google_id=google_id, full_name=name)
            user = crud.user.create(db, obj_in=user_in)
            
    return user

@router.post("/login/google", response_model=schemas.User)
def login_google(
    *,
    db: Session = Depends(deps.get_db),
    token: str
) -> Any:
    """
    Login with Google (using ID token directly).
    """
    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
        
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        google_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name')
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    user = crud.user.get_by_google_id(db, google_id=google_id)
    if not user:
        user = crud.user.get_by_email(db, email=email)
        if user:
            # Link existing user with Google ID
            user = crud.user.update(db, db_obj=user, obj_in={"google_id": google_id})
        else:
            # Create new user
            user_in = schemas.UserCreate(email=email, google_id=google_id, full_name=name)
            user = crud.user.create(db, obj_in=user_in)
            
    return user

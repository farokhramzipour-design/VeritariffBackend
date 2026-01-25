
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as req
import logging

from app import crud, schemas
from app.api import deps
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

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
    response_data = response.json()
    
    if "error" in response_data:
        logger.error(f"Google Token Exchange Error: {response_data}")
        raise HTTPException(status_code=400, detail=f"Google Error: {response_data.get('error_description', response_data)}")

    id_token_str = response_data.get("id_token")
    if not id_token_str:
        logger.error(f"No ID token in response: {response_data}")
        raise HTTPException(status_code=400, detail="No ID token returned from Google")
    
    try:
        id_info = id_token.verify_oauth2_token(id_token_str, requests.Request(), settings.GOOGLE_CLIENT_ID)
        
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        google_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name')
        
    except ValueError as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

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
        
    except ValueError as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

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

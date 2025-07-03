import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from jose import jwt, JWSAlgorithms

from dotenv import load_dotenv

load_dotenv()

# --- Configuration for Google OAuth ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback" # Must match your Google Cloud Console setting
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key") # For your internal JWTs
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- FastAPI App Setup ---
app = FastAPI(
    title="FastAPI OAuth Integrations",
    description="Example for Google and Azure AD authentication",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Session middleware is required for Authlib's OAuth client
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "another-secret-key"))

oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# --- Internal JWT for authenticated users (after Google login) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token") # This tokenUrl is for your API's internal token endpoint, if you had one.
                                                      # For external OAuth, we will issue a token upon successful login.

# Function to create an internal JWT token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Google OAuth Endpoints ---
@app.get("/auth/google/login")
async def login_google(request: Request):
    """
    Redirects to Google for authentication.
    """
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    """
    Handles the callback from Google after successful authentication.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {e}"
        )

    user_info = await oauth.google.parse_id_token(request, token)

    # Here, user_info contains user details from Google (e.g., 'email', 'name', 'sub')
    # You would typically:
    # 1. Look up the user in your database based on their Google ID (user_info['sub'] or 'email').
    # 2. If the user doesn't exist, create a new user record.
    # 3. Create an internal JWT for your application's session.

    # For demonstration, we'll just create a simple JWT
    user_data = {"email": user_info['email'], "name": user_info.get('name', 'N/A'), "google_id": user_info['sub']}
    access_token = create_access_token(data=user_data, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    # Redirect to a frontend page or return the token directly (e.g., for SPA)
    # For a real application, you'd typically redirect to your frontend with the token
    # or set it in a secure cookie.
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response

@app.get("/google-protected-data")
async def get_google_protected_data(request: Request):
    """
    An example protected endpoint.
    Checks for the internal access_token cookie.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("email")
        user_name = payload.get("name")
        google_id = payload.get("google_id")
        if user_email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return {"message": f"Hello, {user_name} ({user_email})! This is Google-protected data.", "google_id": google_id}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>FastAPI OAuth</title>
        </head>
        <body>
            <h1>Welcome to FastAPI OAuth Demo</h1>
            <p><a href="/auth/google/login">Login with Google</a></p>
            <p><a href="/auth/azure/login">Login with Azure AD</a></p>
            <p><a href="/google-protected-data">Access Google Protected Data (after Google login)</a></p>
            <p><a href="/azure-protected-data">Access Azure Protected Data (after Azure login)</a></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
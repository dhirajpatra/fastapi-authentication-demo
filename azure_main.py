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

# --- Azure AD specific imports ---
from fastapi_microsoft_identity import initialize, requires_auth, AuthError, validate_scope

load_dotenv()

# --- Configuration for Google OAuth (already defined above) ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Configuration for Azure AD ---
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID") # Client ID of your API app registration in Azure AD
AZURE_SCOPE = os.getenv("AZURE_SCOPE", "api://YOUR_AZURE_API_APP_ID/access_as_user") # This should be the scope you defined in Azure AD for your API

# Initialize fastapi-microsoft-identity
# Note: This is for validating tokens that *clients* send to your API.
# If your FastAPI app also acts as a client to Azure AD to get tokens for *itself*
# (e.g., if you were to implement a full user login flow initiated by FastAPI redirecting to Azure),
# you'd use Authlib's OAuth.register for 'microsoft' similar to 'google'.
# For now, we're focusing on FastAPI *validating* tokens issued by Azure AD.
try:
    initialize(tenant_id=AZURE_TENANT_ID, client_id=AZURE_CLIENT_ID)
except ValueError as e:
    print(f"Warning: Azure AD initialization failed. Ensure AZURE_TENANT_ID and AZURE_CLIENT_ID are set. Error: {e}")


# --- FastAPI App Setup (already defined above) ---
app = FastAPI(
    title="FastAPI OAuth Integrations",
    description="Example for Google and Azure AD authentication",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "another-secret-key"))

oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# --- Internal JWT for authenticated users (already defined above) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Google OAuth Endpoints (already defined above) ---
@app.get("/auth/google/login")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {e}"
        )

    user_info = await oauth.google.parse_id_token(request, token)
    user_data = {"email": user_info['email'], "name": user_info.get('name', 'N/A'), "google_id": user_info['sub']}
    access_token = create_access_token(data=user_data, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response

@app.get("/google-protected-data")
async def get_google_protected_data(request: Request):
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


# --- Azure AD Protected Endpoint ---
@app.get("/azure-protected-data")
@requires_auth # This decorator from fastapi-microsoft-identity handles token validation
async def get_azure_protected_data(request: Request):
    """
    An example endpoint protected by Azure AD.
    Expects a Bearer token in the Authorization header issued by Azure AD.
    """
    try:
        # Optionally validate specific scopes
        validate_scope(AZURE_SCOPE, request)
        
        # Access token claims after successful validation
        # The claims are available in request.state.user
        claims = request.state.user
        user_name = claims.get("name", "N/A")
        user_email = claims.get("preferred_username", "N/A") # Or 'email'
        tenant_id = claims.get("tid", "N/A")

        return {
            "message": f"Hello, {user_name} ({user_email})! This is Azure AD-protected data.",
            "tenant_id": tenant_id,
            "claims": claims # For debugging, shows all claims
        }
    except AuthError as e:
        # fastapi-microsoft-identity raises AuthError for auth/authz issues
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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
            <p>For Azure AD, you'd typically have a client application (e.g., SPA) that acquires the token and sends it to this API.
            <br>
            If you want to test the Azure AD protected endpoint, you can use a tool like Postman or fetch an access token from Azure AD
            and include it in the 'Authorization: Bearer YOUR_AZURE_AD_TOKEN' header when calling '/azure-protected-data'.
            </p>
            <p><a href="/google-protected-data">Access Google Protected Data (after Google login)</a></p>
            <p><a href="/azure-protected-data">Access Azure Protected Data (needs Azure AD Bearer Token)</a></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
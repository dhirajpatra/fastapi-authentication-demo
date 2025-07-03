# FastAPI OAuth Integration Demo

A demo project showcasing how to integrate Google OAuth2 and Azure Active Directory (Azure AD) authentication into a FastAPI application. This example provides a foundational understanding of secure API authentication using modern identity providers.

## Table of Contents

- [Features](https://www.google.com/search?q=%23features)
- [Prerequisites](https://www.google.com/search?q=%23prerequisites)
- [Getting Started](https://www.google.com/search?q=%23getting-started)
  - [Clone the Repository](https://www.google.com/search?q=%23clone-the-repository)
  - [Install Dependencies](https://www.google.com/search?q=%23install-dependencies)
  - [Environment Variables Setup](https://www.google.com/search?q=%23environment-variables-setup)
    - [Google OAuth2 Configuration](https://www.google.com/search?q=%23google-oauth2-configuration)
    - [Azure AD Configuration](https://www.google.com/search?q=%23azure-ad-configuration)
- [Running the Application](https://www.google.com/search?q=%23running-the-application)
- [API Endpoints](https://www.google.com/search?q=%23api-endpoints)
  - [Google OAuth2 Flow](https://www.google.com/search?q=%23google-oauth2-flow)
  - [Azure AD Protected Endpoint](https://www.google.com/search?q=%23azure-ad-protected-endpoint)
- [Project Structure](https://www.google.com/search?q=%23project-structure)
- [Contributing](https://www.google.com/search?q=%23contributing)
- [License](https://www.google.com/search?q=%23license)

## Features

- **FastAPI Backend:** A robust and high-performance Python API framework.
- **Google OAuth2 Integration:** Implements the Authorization Code Flow for user authentication via Google.
- **Azure Active Directory (Azure AD) Authentication:** Secures API endpoints by validating JWTs issued by Azure AD.
- **Environment Variable Management:** Uses `python-dotenv` for secure configuration.
- **Session Management:** Utilizes `starlette.middleware.sessions` for handling OAuth states.
- **Internal JWTs:** Issues short-lived JWTs for session management after successful external OAuth logins.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+**
- **`pip`** (Python package installer)

You will also need developer accounts and application registrations for:

- **Google Cloud Console:** To set up Google OAuth 2.0 Client ID and Secret.
- **Azure AD (Entra ID) Portal:** To register applications for your API and, optionally, a client application.

## Getting Started

Follow these steps to get the project up and running on your local machine.

### Clone the Repository

```bash
git clone https://github.com/your-username/fastapi-oauth-demo.git # Replace with your repo URL
cd fastapi-oauth-demo
```

### Install Dependencies

```bash
pip install -r requirements.txt
# Or manually:
# pip install fastapi uvicorn python-multipart python-jose[cryptography] authlib python-dotenv fastapi-microsoft-identity
```

### Environment Variables Setup

Create a `.env` file in the root directory of your project and populate it with the following required credentials.

#### Google OAuth2 Configuration

1. **Google Cloud Console Setup:**

      - Go to the [Google Cloud Console](https://console.cloud.google.com/).
      - Create a new project or select an existing one.
      - Navigate to "APIs & Services" \> "Credentials".
      - Click "Create Credentials" \> "OAuth client ID".
      - Select "Web application" as the Application type.
      - Add `http://localhost:8000/auth/google/callback` to "Authorized redirect URIs".
      - After creation, note down your **Client ID** and **Client Secret**.
      - Ensure the "Google People API" (or relevant Google APIs for the scopes you request) is enabled under "Enabled APIs & services".

2. **Add to `.env`:**

    ```dotenv
    GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
    GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"
    ```

#### Azure AD Configuration

1. **Azure AD (Entra ID) Portal Setup:**

      - Go to the [Azure portal](https://portal.azure.com/) and navigate to "Azure Active Directory" (now called Microsoft Entra ID).
      - Go to "App registrations".
      - **Register your FastAPI API as an Application:**
          - Click "New registration".
          - Give it a name (e.g., `FastAPIOAuthDemoAPI`).
          - Supported account types: Choose based on your tenant setup (e.g., "Accounts in this organizational directory only").
          - Don't add a redirect URI for this API app, as it's the *resource server*.
          - After registration, note down its **Application (client) ID** and **Directory (tenant) ID**.
          - Go to "Expose an API":
              - Set an **Application ID URI** (e.g., `api://your-api-app-id`). This is your API's unique identifier.
              - Click "Add a scope" (e.g., `access_as_user`). Define a suitable consent message.
          - Go to "Certificates & secrets":
              - Create a "New client secret". Note down its **Value** (not the ID) immediately, as it's shown only once.
      - **(Optional) Register a Client Application (for testing with Swagger UI or a separate frontend):**
          - Register *another* new application (e.g., `FastAPIOAuthDemoClient`).
          - Under "Authentication", add a "Redirect URI" of type "Single-page application" (SPA) to `http://localhost:8000/oauth2-redirect`.
          - Under "API permissions", click "Add a permission", then "My APIs", select your `FastAPIOAuthDemoAPI`, and choose the scope you defined (e.g., `access_as_user`). Grant admin consent if necessary.
          - Note down its **Application (client) ID** if you plan to use this for Swagger UI authentication.

2. **Add to `.env`:**

    ```dotenv
    AZURE_TENANT_ID="YOUR_AZURE_TENANT_ID" # e.g., your tenant's GUID or 'common' for multi-tenant apps
    AZURE_CLIENT_ID="YOUR_AZURE_API_APP_ID" # The Application (client) ID of your FastAPI API registration in Azure AD
    AZURE_SCOPE="api://YOUR_AZURE_API_APP_ID/access_as_user" # The full scope string you defined in Azure AD
    ```

#### Internal Project Secrets

```dotenv
# Used for signing internal JWTs after successful external OAuth logins
JWT_SECRET_KEY="a-very-strong-and-random-secret-key-for-your-jwt"

# Used by the Starlette Session Middleware (for OAuth state management)
SESSION_SECRET_KEY="another-long-random-string-for-session-middleware"
```

**Important:** Replace all placeholder values (`YOUR_...`) with your actual credentials. Never commit your `.env` file to version control.

## Running the Application

1. Ensure all environment variables are set in your `.env` file.

2. Start the FastAPI application using Uvicorn:

    ```bash
    uvicorn main:app --reload
    ```

    The application will be accessible at `http://localhost:8000`.

## API Endpoints

### Google OAuth2 Flow

These endpoints facilitate the Google login process:

- **`GET /auth/google/login`**:
  - Initiates the Google OAuth2 login flow. Redirects the user to Google's authentication page.
- **`GET /auth/google/callback`**:
  - Handles the callback from Google after successful user authentication.
  - Exchanges the authorization code for tokens, fetches user information, and issues an internal JWT (stored as an `access_token` cookie for this demo).
  - Redirects to the home page (`/`) on success.
- **`GET /google-protected-data`**:
  - **Protected Endpoint:** Requires a valid internal JWT (issued after Google login) in the `access_token` cookie.
  - Demonstrates access to a resource only after successful Google authentication.

**How to test Google OAuth:**

1. Open your browser to `http://localhost:8000`.
2. Click "Login with Google".
3. Follow the Google login and consent prompts.
4. You will be redirected back to the home page.
5. Click "Access Google Protected Data" to verify your session.

### Azure AD Protected Endpoint

This endpoint requires a valid JWT issued by Azure AD in the `Authorization` header.

- **`GET /azure-protected-data`**:
  - **Protected Endpoint:** Requires a `Bearer` token (JWT) issued by Azure AD in the `Authorization` header (`Authorization: Bearer YOUR_AZURE_AD_TOKEN`).
  - The `fastapi-microsoft-identity` library handles the token validation (signature, issuer, audience, expiration) and scope validation (`AZURE_SCOPE`).
  - Returns user claims extracted from the token if valid.

**How to test Azure AD Protected Endpoint:**

Since your FastAPI application acts as the Resource Server for Azure AD, it expects an access token to be provided by a client. You'll need to obtain an Azure AD access token from a client application (e.g., a Single Page Application, mobile app, or a tool like Postman) and then send it to this API.

**Using Postman/Insomnia/curl:**

1. **Obtain an Azure AD Access Token:** This is the most crucial step. You can use:

      - **Azure AD's Device Code Flow:** For CLI tools or simple testing. (Search for "Azure AD Device Code Flow Postman" for guides).
      - **Azure AD Client Credentials Flow:** If your API is called by another service (machine-to-machine).
      - **A separate frontend application:** A React/Angular/Vue app configured to authenticate with Azure AD and acquire tokens.

2. **Make an API Request:** Once you have the Azure AD access token, send a GET request to `http://localhost:8000/azure-protected-data` with the `Authorization` header:

    ```http
    GET http://localhost:8000/azure-protected-data
    Authorization: Bearer YOUR_AZURE_AD_ACCESS_TOKEN
    ```

## Project Structure

```
.
├── main.py                 # Main FastAPI application with endpoints and OAuth logic
├── .env                    # Environment variables (Google/Azure credentials, JWT secrets)
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation (this file)
```

## Contributing

Feel free to fork this repository, make improvements, and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details (if you have one, otherwise remove this line).

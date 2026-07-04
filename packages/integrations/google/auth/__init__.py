import os
import jwt
import datetime
import asyncpg
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

SCOPES = [
    'openid', 
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify'
]

oauth_state_store = {}

def get_google_flow():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret or client_secret == "YOUR_CLIENT_SECRET_HERE":
        raise ValueError("Google Client ID and Secret are not configured in .env")

    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": "chief-ai-os",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:3000/api/auth/google/callback"]
        }
    }
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri="http://localhost:3000/api/auth/google/callback"
    )
    return flow

async def handle_google_callback(state: str, code: str, vault_store_fn):
    """
    Handles the Google OAuth callback:
    1. Fetches credentials
    2. Fetches user profile
    3. Upserts user in Neon DB
    4. Stores credentials in vault and DB
    5. Generates JWT
    """
    tenant_id = state  # We passed tenant_id as state
    flow = get_google_flow()
    
    code_verifier = oauth_state_store.get(state)
    if code_verifier:
        flow.code_verifier = code_verifier
        
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    creds_dict = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    # Fetch User Profile
    oauth2_service = build('oauth2', 'v2', credentials=credentials)
    user_info = oauth2_service.userinfo().get().execute()
    email = user_info.get('email')
    name = user_info.get('name')
    picture = user_info.get('picture')
    google_id = user_info.get('id')
    
    # Get DB URL
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")
    if "?" in db_url: db_url = db_url.split("?")[0]
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Upsert User
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
        if user_id:
            await conn.execute(
                "UPDATE users SET name = $1, auth_provider_ref = $2 WHERE id = $3",
                name, google_id, user_id
            )
        else:
            user_id = await conn.fetchval(
                """
                INSERT INTO users (tenant_id, email, name, role, auth_provider_ref)
                VALUES ($1, $2, $3, 'founder', $4)
                RETURNING id
                """,
                tenant_id, email, name, google_id
            )
            
        # Store in Vault
        vault_ref = vault_store_fn("google", tenant_id, creds_dict)
        
        # Store Integration mapping
        exists = await conn.fetchval("SELECT id FROM integrations WHERE tenant_id = $1 AND provider = 'google'", tenant_id)
        if exists:
            await conn.execute(
                "UPDATE integrations SET credential_vault_ref = $1, status = 'active', updated_at = NOW() WHERE id = $2",
                vault_ref, exists
            )
        else:
            await conn.execute(
                "INSERT INTO integrations (tenant_id, provider, category, credential_vault_ref, status) VALUES ($1, 'google', 'productivity', $2, 'active')",
                tenant_id, vault_ref
            )
            
        # Generate JWT
        jwt_secret = os.environ.get("JWT_SECRET", "changeme_jwt_secret")
        jwt_issuer = os.environ.get("JWT_ISSUER", "chief-dev")
        
        token = jwt.encode(
            {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "role": "founder",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                "iss": jwt_issuer
            },
            jwt_secret,
            algorithm="HS256"
        )
        
        return {
            "token": token,
            "user": {
                "id": str(user_id),
                "name": name,
                "email": email,
                "avatar_url": picture
            }
        }
    finally:
        await conn.close()

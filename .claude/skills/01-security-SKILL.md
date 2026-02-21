# Skill: Security Fixes (P0 Priority)

## Critical Issues to Fix

### 1. JWT Secret Key Hardcoded
**File**: `backend/app/config.py`
**Problem**: `JWT_SECRET_KEY: str = "evalora-secret-key-change-in-production-2024"` is hardcoded.
**Fix**:
```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OPENAI_API_KEY: str
    ELEVENLABS_API_KEY: str = ""
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    TAVUS_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 2. DATABASE_URL Exposed
**File**: `backend/app/config.py`  
**Problem**: Neon connection string may be hardcoded.  
**Fix**: Must come from `.env` via `Settings()` above.

### 3. Create .env.example
**File**: `backend/.env.example` (NEW)
```env
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
TAVUS_API_KEY=...
```

### 4. Update .gitignore
Ensure these are listed:
```
.env
*.env
backend/.env
agent/.env
frontend/.env
```

### 5. CORS Configuration
**File**: `backend/app/main.py`
**Problem**: `allow_origins=["*"]` in production is dangerous.
**Fix**:
```python
from app.config import settings

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    # Add production domain when deploying
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Validation Checklist
After applying fixes, verify:
```bash
# 1. No secrets in code
grep -rn "evalora-secret-key" backend/ --include="*.py"
# Should return 0 results

# 2. .env exists and is loaded
cd backend && python -c "from app.config import settings; print(settings.JWT_SECRET_KEY[:5])"
# Should print first 5 chars of your real key

# 3. .gitignore works
git status | grep ".env"
# Should not show .env files

# 4. Generate a proper JWT secret
python -c "import secrets; print(secrets.token_hex(32))"
```

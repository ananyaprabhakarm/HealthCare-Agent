import os

# app.auth fails fast at import time if JWT_SECRET is unset — make sure
# tests always have one, without needing a real .env file.
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-production")

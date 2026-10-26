import os

from dotenv import load_dotenv


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "10000"))
MAX_COST = float(os.getenv("MAX_COST", "0.10"))

# Send the session cookie over HTTPS only. Keep false for local http.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# Browser origins allowed to call the API (CORS and the CSRF origin check).
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]


if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")
import logging
import os

from dotenv import load_dotenv


# uvicorn decides which proxies to trust before this module runs, so the
# value only counts if it was in the environment already (--env-file .env).
# Checked before load_dotenv(), which would hide a missing --env-file.
if "FORWARDED_ALLOW_IPS" not in os.environ:
    logging.getLogger(__name__).warning(
        "FORWARDED_ALLOW_IPS is not set, so uvicorn trusts X-Forwarded-For "
        "from 127.0.0.1 and client IPs (login limits) can be spoofed. "
        "Start uvicorn with --env-file .env."
    )

load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "10000"))
MAX_COST = float(os.getenv("MAX_COST", "0.10"))

# Send the session cookie over HTTPS only. Safe by default; set false
# only for local development over plain http.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"

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
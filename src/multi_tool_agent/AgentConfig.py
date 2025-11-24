from google.genai import types
from google.adk.models.google_llm import Gemini
import os
from google.adk.sessions.database_session_service import DatabaseSessionService
from dotenv import load_dotenv
load_dotenv() # Load environment variables from a .env file if present
# --- Define Model Constants for easier use ---
AGENT_MODEL = os.getenv("MODEL_NAME","gemini-2.5-flash")
LLM_AS_JUDEGE_MODEL = os.getenv("LLM_AS_JUDGE_MODEL","gemini-2.5-flash")


retry_config=types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504], # Retry on these HTTP errors
)
base_model=Gemini(model=AGENT_MODEL, retry_options=retry_config)



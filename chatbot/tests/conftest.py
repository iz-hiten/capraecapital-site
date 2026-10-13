import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["LOG_FILE"] = os.path.join(tempfile.gettempdir(), "caprae-chatbot-test.log")
os.environ["ALLOWED_ORIGINS"] = "https://capraecapital.com"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["TURNSTILE_SECRET"] = ""
os.environ["PER_IP_PER_MINUTE"] = "1000"
os.environ["PER_IP_PER_DAY"] = "1000"

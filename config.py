"""Configuration for the Insurance Claims Processing Agent."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'claims-agent-secret-key-2024')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    FAST_TRACK_THRESHOLD = 25000  # ₹25,000 in INR
    CURRENCY_SYMBOL = '₹'
    CURRENCY_NAME = 'INR'
import os
from datetime import timedelta

class Config:
    # Supabase configuration  
    # Get these from: Supabase Dashboard > Settings > API
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL environment variable is required!")
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY environment variable is required!")
    
    # JWT configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # CORS configuration
    CORS_HEADERS = 'Content-Type'
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')  # or 'gpt-3.5-turbo' for faster/cheaper

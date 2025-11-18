from supabase import create_client, Client
from flask import current_app, g

def init_supabase(app):
    """Initialize Supabase client"""
    url = app.config['SUPABASE_URL']
    key = app.config['SUPABASE_KEY']
    return create_client(url, key)

def get_supabase() -> Client:
    """Get Supabase client for current request"""
    if 'supabase' not in g:
        g.supabase = create_client(
            current_app.config['SUPABASE_URL'],
            current_app.config['SUPABASE_KEY']
        )
    return g.supabase


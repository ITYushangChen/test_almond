from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from supabase_client import init_supabase
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.analysis import analysis_bp
from routes.benchmark import benchmark_bp
from routes.ai_analysis import ai_analysis_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    CORS(app)
    JWTManager(app)
    
    # Initialize Supabase client
    with app.app_context():
        supabase = init_supabase(app)
        print(f"✓ Connected to Supabase: {app.config['SUPABASE_URL']}")
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(benchmark_bp, url_prefix='/api/benchmark')
    app.register_blueprint(ai_analysis_bp, url_prefix='/api/ai-analysis')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)


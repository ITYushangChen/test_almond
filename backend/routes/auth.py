from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from supabase_client import get_supabase

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    supabase = get_supabase()
    
    # Check if user exists
    response = supabase.table('users').select('*').eq('username', username).execute()
    if response.data:
        return jsonify({'error': 'Username already exists'}), 409
    
    # Create user
    password_hash = generate_password_hash(password)
    supabase.table('users').insert({
        'username': username,
        'password_hash': password_hash
    }).execute()
    
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    supabase = get_supabase()
    
    # Find user
    response = supabase.table('users').select('*').eq('username', username).execute()
    
    if not response.data:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    user = response.data[0]
    
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    access_token = create_access_token(identity=username)
    return jsonify({'access_token': access_token, 'username': username}), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    return jsonify({'username': current_user}), 200

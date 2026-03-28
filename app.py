import pickle
import numpy as np
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from model.SpellChecker import SpellChecker ,spell_preprocessor
from model.CustomPreprocessor import CustomPreprocessor
from model.RecipeSearchEngine import RecipeSearchEngine
from model.ImageCollection import ImageCollection
from model.User import db, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cookmai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

with open('resource/recipe_search_engine.pkl', 'rb') as f:
    search_engine = pickle.load(f)

with open('resource/image_collection.pkl', 'rb') as f:
    image_collection = pickle.load(f)

with open('resource/spell_collection.pkl', 'rb') as f:
    spell_checker = pickle.load(f)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def create_tables():
    if not os.path.exists('cookmai.db'):
        with app.app_context():
            db.create_all()

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '').lower()
    return render_template('search.html', query=query)

@app.route('/api/search', methods=['GET'])
@login_required
def api_search():
    query = request.args.get('q', '').lower()

    if not query.strip():
        return jsonify({
            "error": "Please enter a search query",
            "results": []
        }), 400

    query_words = query.split()

    corrected_words = []
    has_typo = False

    for word in query_words:
        corrected = spell_checker.correction(word)
        if corrected != word:
            has_typo = True
        corrected_words.append(corrected)

    suggested_query = " ".join(corrected_words)

    results_df = search_engine.search(query, top_k=10)

    print("DataFrame columns:", results_df.columns.tolist())

    results = results_df.to_dict(orient='records')

    for recipe in results:
        recipe_id = recipe.get('RecipeId') or recipe.get('recipe_id') or recipe.get('Id') or recipe.get('id')

        if recipe_id:
            image_urls = image_collection.get_urls(recipe_id)
            recipe['Images'] = image_urls[0] if image_urls else ''
        else:
            recipe['Images'] = ''

        for key, value in recipe.items():
            if isinstance(value, float) and np.isnan(value):
                recipe[key] = None

    return jsonify({
        "original_query": query,
        "has_typo": has_typo,
        "suggested_query": suggested_query if has_typo else "",
        "results": results
    })

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Registration successful"}), 201

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return jsonify({
            "message": "Login successful",
            "username": user.username
        }), 200

    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "username": current_user.username
        }), 200
    return jsonify({"authenticated": False}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5678)

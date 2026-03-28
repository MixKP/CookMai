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
from model.User import db, User, Folder, Bookmark

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

@app.route('/folders')
@login_required
def folders_page():
    return render_template('folders.html')

@app.route('/api/folders', methods=['GET'])
@login_required
def get_folders():
    folders = Folder.query.filter_by(user_id=current_user.id).order_by(Folder.created_at.desc()).all()
    return jsonify([{
        'id': f.id,
        'name': f.name,
        'description': f.description,
        'icon': f.icon,
        'bookmark_count': len(f.bookmarks),
        'created_at': f.created_at.isoformat() if f.created_at else None
    } for f in folders])

@app.route('/api/folders', methods=['POST'])
@login_required
def create_folder():
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    icon = data.get('icon', '📁')

    if not name:
        return jsonify({'error': 'Folder name is required'}), 400

    if len(name) > 100:
        return jsonify({'error': 'Folder name must be less than 100 characters'}), 400

    folder = Folder(
        user_id=current_user.id,
        name=name,
        description=description or None,
        color='none',
        icon=icon
    )
    db.session.add(folder)
    db.session.commit()

    return jsonify({
        'message': 'Folder created',
        'folder': {
            'id': folder.id,
            'name': folder.name,
            'description': folder.description,
            'icon': folder.icon,
            'bookmark_count': 0,
            'created_at': folder.created_at.isoformat()
        }
    }), 201

@app.route('/api/folders/<int:folder_id>', methods=['PUT'])
@login_required
def update_folder(folder_id):
    folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()

    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    icon = data.get('icon', '📁')

    if not name:
        return jsonify({'error': 'Folder name is required'}), 400

    if len(name) > 100:
        return jsonify({'error': 'Folder name must be less than 100 characters'}), 400

    folder.name = name
    folder.description = description or None
    folder.icon = icon
    db.session.commit()

    return jsonify({
        'message': 'Folder updated',
        'folder': {
            'id': folder.id,
            'name': folder.name,
            'description': folder.description,
            'icon': folder.icon,
            'bookmark_count': len(folder.bookmarks),
            'created_at': folder.created_at.isoformat()
        }
    })

@app.route('/api/folders/<int:folder_id>', methods=['DELETE'])
@login_required
def delete_folder(folder_id):
    folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()

    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    db.session.delete(folder)
    db.session.commit()

    return jsonify({'message': 'Folder deleted'})

@app.route('/api/folders/<int:folder_id>/bookmarks', methods=['GET'])
@login_required
def get_folder_bookmarks(folder_id):
    folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()

    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    bookmarks = Bookmark.query.filter_by(folder_id=folder_id).order_by(Bookmark.created_at.desc()).all()

    recipe_ids = [b.recipe_id for b in bookmarks]

    return jsonify([{
        'id': b.id,
        'recipe_id': b.recipe_id,
        'recipe_name': b.recipe_name,
        'user_rating': b.user_rating,
        'notes': b.notes,
        'created_at': b.created_at.isoformat() if b.created_at else None
    } for b in bookmarks])

@app.route('/api/bookmarks', methods=['POST'])
@login_required
def add_bookmark():
    data = request.get_json()
    folder_id = data.get('folder_id')
    recipe_id = data.get('recipe_id')
    recipe_name = data.get('recipe_name', '').strip()
    user_rating = data.get('user_rating')
    notes = data.get('notes', '').strip()

    if not folder_id or not recipe_id or not recipe_name:
        return jsonify({'error': 'folder_id, recipe_id, and recipe_name are required'}), 400

    folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    existing = Bookmark.query.filter_by(user_id=current_user.id, folder_id=folder_id, recipe_id=recipe_id).first()
    if existing:
        return jsonify({'error': 'Recipe already bookmarked in this folder'}), 400

    bookmark = Bookmark(
        user_id=current_user.id,
        folder_id=folder_id,
        recipe_id=recipe_id,
        recipe_name=recipe_name,
        user_rating=user_rating if user_rating is not None else None,
        notes=notes or None
    )
    db.session.add(bookmark)
    db.session.commit()

    return jsonify({
        'message': 'Bookmark added',
        'bookmark': {
            'id': bookmark.id,
            'recipe_id': bookmark.recipe_id,
            'recipe_name': bookmark.recipe_name,
            'user_rating': bookmark.user_rating
        }
    }), 201

@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def delete_bookmark(bookmark_id):
    bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=current_user.id).first()

    if not bookmark:
        return jsonify({'error': 'Bookmark not found'}), 404

    db.session.delete(bookmark)
    db.session.commit()

    return jsonify({'message': 'Bookmark removed'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5678)

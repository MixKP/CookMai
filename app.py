import os
import pickle
from datetime import timezone, timedelta

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from model.RecipeSearchEngine import RecipeSearchEngine
from model.CustomPreprocessor import CustomPreprocessor
from model.BM25Transformer import BM25Transformer
from model.SpellChecker import SpellChecker
from model.ImageCollection import ImageCollection
from model.User import db, User, Folder, Bookmark
from model.RecommendationModel import RecommendationModel

from services.recipe_service import RecipeService
from services.folder_service import FolderService
from services.bookmark_service import BookmarkService
from services.recommendation_service import RecommendationService
from validators.category_validator import CategoryValidatorFactory


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

with open('resource/recipes.pkl', 'rb') as f:
    recipes_df_full = pickle.load(f)

with open('resource/image_collection.pkl', 'rb') as f:
    image_collection = pickle.load(f)

with open('resource/spell_collection.pkl', 'rb') as f:
    spell_checker = pickle.load(f)

recommendation_model = RecommendationModel(
    'resource/recipe_recommendation_model.pkl',
    'resource/recipes.pkl'
)

THAILAND_TZ = timezone(timedelta(hours=7))


def convert_to_thailand_time(utc_datetime):
    if utc_datetime is None:
        return None
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    return utc_datetime.astimezone(THAILAND_TZ)


recipe_service = RecipeService(search_engine, image_collection, recipes_df_full)
folder_service = FolderService(convert_to_thailand_time)
bookmark_service = BookmarkService(convert_to_thailand_time)
category_validator = CategoryValidatorFactory.create_default_validator()
recommendation_service = RecommendationService(
    recipes_df_full,
    image_collection,
    recommendation_model,
    category_validator
)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


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


@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '').lower()
    return render_template('search.html', query=query)


@app.route('/folders')
@login_required
def folders_page():
    return render_template('folders.html')


@app.route('/bookmarks')
@login_required
def bookmarks_page():
    return render_template('bookmarks.html')


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


@app.route('/api/search', methods=['GET'])
@login_required
def api_search():
    query = request.args.get('q', '').lower()
    result = recipe_service.search_recipes(query, spell_checker)

    if not result:
        return jsonify({
            "error": "Please enter a search query",
            "results": []
        }), 400

    return jsonify(result)


@app.route('/api/recipes/<int:recipe_id>', methods=['GET'])
@login_required
def get_recipe_detail(recipe_id):
    recipe = recipe_service.get_recipe_by_id(recipe_id)

    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404

    return jsonify(recipe)


@app.route('/api/folders', methods=['GET'])
@login_required
def get_folders():
    folders = folder_service.get_user_folders(current_user.id)
    return jsonify([folder_service.folder_to_dict(f) for f in folders])


@app.route('/api/folders', methods=['POST'])
@login_required
def create_folder():
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    icon = data.get('icon', '📁')

    try:
        folder = folder_service.create_folder(current_user.id, name, description, icon)
        return jsonify({
            'message': 'Folder created',
            'folder': folder_service.folder_to_dict(folder)
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/folders/<int:folder_id>', methods=['PUT'])
@login_required
def update_folder(folder_id):
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    icon = data.get('icon', '📁')

    try:
        folder = folder_service.update_folder(folder_id, current_user.id, name, description, icon)
        if not folder:
            return jsonify({'error': 'Folder not found'}), 404

        return jsonify({
            'message': 'Folder updated',
            'folder': folder_service.folder_to_dict(folder)
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/folders/<int:folder_id>', methods=['DELETE'])
@login_required
def delete_folder(folder_id):
    if not folder_service.delete_folder(folder_id, current_user.id):
        return jsonify({'error': 'Folder not found'}), 404

    return jsonify({'message': 'Folder deleted'})


@app.route('/api/folders/<int:folder_id>/bookmarks', methods=['GET'])
@login_required
def get_folder_bookmarks(folder_id):
    folder = folder_service.get_folder_by_id(folder_id, current_user.id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    bookmarks = bookmark_service.get_folder_bookmarks(folder_id, current_user.id)
    return jsonify([bookmark_service.bookmark_to_dict(b) for b in bookmarks])


@app.route('/api/folders/<int:folder_id>/suggestions', methods=['GET'])
@login_required
def get_folder_suggestions(folder_id):
    folder = folder_service.get_folder_by_id(folder_id, current_user.id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    bookmarks = Bookmark.query.filter_by(folder_id=folder_id).all()
    if not bookmarks:
        return jsonify({
            'error': 'Folder is empty',
            'message': 'Add some recipes to this folder first to get personalized suggestions!'
        }), 400

    try:
        recommendations = recommendation_service.get_folder_suggestions(folder_id, current_user.id, bookmarks)
        if not recommendations:
            return jsonify({
                'error': 'No recommendations available',
                'message': 'Could not generate suggestions for this folder'
            }), 404

        return jsonify({
            'folder_name': folder.name,
            'folder_size': len(bookmarks),
            'recommendations': recommendations
        })

    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return jsonify({
            'error': 'Failed to generate recommendations',
            'message': str(e)
        }), 500


@app.route('/api/bookmarks', methods=['POST'])
@login_required
def add_bookmark():
    data = request.get_json()
    folder_id = data.get('folder_id')
    recipe_id = data.get('recipe_id')
    recipe_name = data.get('recipe_name', '').strip()
    user_rating = data.get('user_rating')
    notes = data.get('notes', '').strip()

    try:
        bookmark = bookmark_service.add_bookmark(
            current_user.id,
            folder_id,
            recipe_id,
            recipe_name,
            user_rating,
            notes
        )
        return jsonify({
            'message': 'Bookmark added',
            'bookmark': {
                'id': bookmark.id,
                'recipe_id': bookmark.recipe_id,
                'recipe_name': bookmark.recipe_name,
                'user_rating': bookmark.user_rating
            }
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def delete_bookmark(bookmark_id):
    if not bookmark_service.delete_bookmark(bookmark_id, current_user.id):
        return jsonify({'error': 'Bookmark not found'}), 404

    return jsonify({'message': 'Bookmark removed'})


@app.route('/api/bookmarks/all', methods=['GET'])
@login_required
def get_all_bookmarks():
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).join(Folder)\
        .order_by(Bookmark.user_rating.desc(), Bookmark.recipe_name.asc()).all()

    return jsonify([{
        'id': b.id,
        'recipe_id': b.recipe_id,
        'recipe_name': b.recipe_name,
        'user_rating': b.user_rating,
        'folder_id': b.folder_id,
        'folder_name': b.folder.name if b.folder else 'Unknown',
        'folder_icon': b.folder.icon if b.folder else '📁',
        'created_at': convert_to_thailand_time(b.created_at).isoformat() if b.created_at else None
    } for b in bookmarks])


@app.route('/api/recommendations', methods=['GET'])
@login_required
def get_recommendations():
    selected_category = request.args.get('category')
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()

    return jsonify(recommendation_service.get_recommendations(current_user.id, bookmarks, selected_category))


@app.route('/api/recommendations/categories', methods=['GET'])
@login_required
def get_recommendation_categories():
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()
    if not bookmarks:
        return jsonify({'categories': []})

    all_bookmarked_ids = [b.recipe_id for b in bookmarks]
    bookmarked_recipes = recipes_df_full[recipes_df_full['RecipeId'].isin(all_bookmarked_ids)]
    if bookmarked_recipes.empty:
        return jsonify({'categories': []})

    categories = bookmarked_recipes['RecipeCategory'].dropna().unique().tolist()
    valid_categories = sorted([c for c in categories if category_validator.is_valid(c)])

    return jsonify({'categories': valid_categories})


@app.route('/api/categories/all', methods=['GET'])
@login_required
def get_all_categories():
    all_categories = recipes_df_full['RecipeCategory'].dropna().unique().tolist()
    valid_categories = sorted([c for c in all_categories if category_validator.is_valid(c)])

    return jsonify({'categories': valid_categories})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5678)

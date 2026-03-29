import pickle
import numpy as np
import os
from datetime import datetime, timezone, timedelta
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

with open('resource/recipes.pkl', 'rb') as f:
    recipes_df_full = pickle.load(f)

with open('resource/image_collection.pkl', 'rb') as f:
    image_collection = pickle.load(f)

with open('resource/spell_collection.pkl', 'rb') as f:
    spell_checker = pickle.load(f)

# Thailand timezone (UTC+7)
THAILAND_TZ = timezone(timedelta(hours=7))

def convert_to_thailand_time(utc_datetime):
    """Convert UTC datetime to Thailand timezone (UTC+7)"""
    if utc_datetime is None:
        return None
    # Assume input is in UTC if it's naive (no timezone info)
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    return utc_datetime.astimezone(THAILAND_TZ)

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

    results_df = search_engine.search(suggested_query, top_k=10)

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

@app.route('/api/recipes/<int:recipe_id>', methods=['GET'])
@login_required
def get_recipe_detail(recipe_id):
    recipe_data = recipes_df_full[recipes_df_full['RecipeId'] == recipe_id]

    if recipe_data.empty:
        return jsonify({'error': 'Recipe not found'}), 404

    recipe = recipe_data.iloc[0].to_dict()

    rid = recipe.get('RecipeId')
    if rid:
        image_urls = image_collection.get_urls(rid)
        recipe['Images'] = image_urls[0] if image_urls else ''
    else:
        recipe['Images'] = ''

    for key, value in recipe.items():
        if isinstance(value, float) and np.isnan(value):
            recipe[key] = None

    return jsonify(recipe)

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

@app.route('/bookmarks')
@login_required
def bookmarks_page():
    return render_template('bookmarks.html')

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
        'created_at': convert_to_thailand_time(f.created_at).isoformat() if f.created_at else None
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
            'created_at': convert_to_thailand_time(folder.created_at).isoformat() if folder.created_at else None
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
            'created_at': convert_to_thailand_time(folder.created_at).isoformat() if folder.created_at else None
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

    bookmarks = Bookmark.query.filter_by(folder_id=folder_id).order_by(Bookmark.user_rating.desc(), Bookmark.recipe_name.asc()).all()

    return jsonify([{
        'id': b.id,
        'recipe_id': b.recipe_id,
        'recipe_name': b.recipe_name,
        'user_rating': b.user_rating,
        'notes': b.notes,
        'created_at': convert_to_thailand_time(b.created_at).isoformat() if b.created_at else None
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

@app.route('/api/bookmarks/all', methods=['GET'])
@login_required
def get_all_bookmarks():
    from sqlalchemy import desc

    # Fetch bookmarks ordered by rating (descending), then name (ascending)
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).join(Folder)\
        .order_by(Bookmark.user_rating.desc(), Bookmark.recipe_name.asc()).all()

    result = []
    for b in bookmarks:
        folder = Folder.query.get(b.folder_id)
        result.append({
            'id': b.id,
            'recipe_id': b.recipe_id,
            'recipe_name': b.recipe_name,
            'user_rating': b.user_rating,
            'folder_id': b.folder_id,
            'folder_name': folder.name if folder else 'Unknown',
            'folder_icon': folder.icon if folder else '📁',
            'created_at': convert_to_thailand_time(b.created_at).isoformat() if b.created_at else None
        })

    return jsonify(result)

@app.route('/api/recommendations/categories', methods=['GET'])
@login_required
def get_recommendation_categories():
    import re

    # Get all user bookmarks
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()

    if not bookmarks:
        return jsonify({'categories': []})

    # Get all bookmarked recipe IDs
    all_bookmarked_ids = [b.recipe_id for b in bookmarks]
    bookmarked_recipes = recipes_df_full[recipes_df_full['RecipeId'].isin(all_bookmarked_ids)]

    if bookmarked_recipes.empty:
        return jsonify({'categories': []})

    # Get all categories
    categories = bookmarked_recipes['RecipeCategory'].dropna().unique().tolist()

    # Filter out number and time-based categories
    def is_valid_category(category):
        category_str = str(category).lower().strip()

        # Skip if category is mostly numbers
        if re.match(r'^[\d\s]+$', category_str):
            return False

        # Skip if contains time indicators
        time_keywords = ['min', 'mins', 'minute', 'minutes', 'hr', 'hrs', 'hour', 'hours',
                        'less', 'under', 'over', 'more', 'within', '<', '>', '≤', '≥']
        if any(keyword in category_str for keyword in time_keywords):
            return False

        # Skip if starts with a number
        if category_str and category_str[0].isdigit():
            return False

        return True

    valid_categories = [c for c in categories if is_valid_category(c)]

    # Sort categories alphabetically
    valid_categories.sort()

    return jsonify({'categories': valid_categories})

@app.route('/api/categories/all', methods=['GET'])
@login_required
def get_all_categories():
    import re

    # Get all unique categories from the entire recipe database
    all_categories = recipes_df_full['RecipeCategory'].dropna().unique().tolist()

    # Filter out number and time-based categories
    def is_valid_category(category):
        category_str = str(category).lower().strip()

        # Skip if category is mostly numbers
        if category_str and category_str[0].isdigit():
            return False

        # Skip if contains time indicators
        time_keywords = ['min', 'mins', 'minute', 'minutes', 'hr', 'hrs', 'hour', 'hours',
                        'less', 'under', 'over', 'more', 'within', '<', '>', '≤', '≥']
        if any(keyword in category_str for keyword in time_keywords):
            return False

        return True

    valid_categories = [c for c in all_categories if is_valid_category(c)]

    # Sort categories alphabetically
    valid_categories.sort()

    return jsonify({'categories': valid_categories})

@app.route('/api/recommendations', methods=['GET'])
@login_required
def get_recommendations():
    import random

    # Get optional category filter
    selected_category = request.args.get('category')

    # Get all user bookmarks
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()

    if not bookmarks:
        return jsonify({
            'from_bookmarks': [],
            'category_picks': [],
            'random_discoveries': []
        })

    # 1. From Your Bookmarks - get up to 6 top-rated bookmarks
    from_bookmarks_data = sorted(bookmarks, key=lambda x: x.user_rating or 0, reverse=True)[:6]

    from_bookmarks = []
    for b in from_bookmarks_data:
        recipe_data = recipes_df_full[recipes_df_full['RecipeId'] == b.recipe_id]
        if not recipe_data.empty:
            recipe = recipe_data.iloc[0].to_dict()
            rid = recipe.get('RecipeId')
            if rid:
                image_urls = image_collection.get_urls(rid)
                recipe['Images'] = image_urls[0] if image_urls else ''

            for key, value in recipe.items():
                if isinstance(value, float) and np.isnan(value):
                    recipe[key] = None

            from_bookmarks.append({
                'recipe_id': recipe['RecipeId'],
                'recipe_name': recipe['Name'],
                'image': recipe['Images'],
                'category': recipe.get('RecipeCategory', '—'),
                'rating': recipe.get('AggregatedRating'),
                'user_rating': b.user_rating,
                'folder_name': b.folder.name if b.folder else 'Unknown'
            })

    # 2. Category Picks - pick a random category from user's bookmarks and get 6 recipes
    all_bookmarked_ids = [b.recipe_id for b in bookmarks]
    bookmarked_recipes = recipes_df_full[recipes_df_full['RecipeId'].isin(all_bookmarked_ids)]

    # Filter out number and time-based categories
    def is_valid_category(category):
        category_str = str(category).lower().strip()

        # Skip if category is mostly numbers
        if category_str and category_str[0].isdigit():
            return False

        # Skip if contains time indicators
        time_keywords = ['min', 'mins', 'minute', 'minutes', 'hr', 'hrs', 'hour', 'hours',
                        'less', 'under', 'over', 'more', 'within', '<', '>', '≤', '≥']
        if any(keyword in category_str for keyword in time_keywords):
            return False

        return True

    # If user selected a specific category, use it
    if selected_category:
        # Get 6 recipes from selected category (excluding user's bookmarks)
        category_recipes = recipes_df_full[
            (recipes_df_full['RecipeCategory'] == selected_category) &
            (~recipes_df_full['RecipeId'].isin(all_bookmarked_ids))
        ]

        if len(category_recipes) > 0:
            # Sample up to 6 recipes
            category_sample = category_recipes.sample(n=min(6, len(category_recipes)), random_state=42)

            category_picks = []
            for _, recipe in category_sample.iterrows():
                recipe_dict = recipe.to_dict()
                rid = recipe_dict.get('RecipeId')
                if rid:
                    image_urls = image_collection.get_urls(rid)
                    recipe_dict['Images'] = image_urls[0] if image_urls else ''

                for key, value in recipe_dict.items():
                    if isinstance(value, float) and np.isnan(value):
                        recipe_dict[key] = None

                category_picks.append({
                    'recipe_id': recipe_dict['RecipeId'],
                    'recipe_name': recipe_dict['Name'],
                    'image': recipe_dict['Images'],
                    'category': recipe_dict.get('RecipeCategory', '—'),
                    'rating': recipe_dict.get('AggregatedRating')
                })
        else:
            category_picks = []
            selected_category = None
    elif not bookmarked_recipes.empty:
        # Get all categories from user's bookmarks
        categories = bookmarked_recipes['RecipeCategory'].dropna().unique().tolist()
        categories = [c for c in categories if is_valid_category(c)]

        if categories:
            # Pick a random category
            selected_category = random.choice(categories)

            # Get 6 recipes from this category (excluding user's bookmarks)
            category_recipes = recipes_df_full[
                (recipes_df_full['RecipeCategory'] == selected_category) &
                (~recipes_df_full['RecipeId'].isin(all_bookmarked_ids))
            ]

            if len(category_recipes) > 0:
                # Sample up to 6 recipes
                category_sample = category_recipes.sample(n=min(6, len(category_recipes)), random_state=42)

                category_picks = []
                for _, recipe in category_sample.iterrows():
                    recipe_dict = recipe.to_dict()
                    rid = recipe_dict.get('RecipeId')
                    if rid:
                        image_urls = image_collection.get_urls(rid)
                        recipe_dict['Images'] = image_urls[0] if image_urls else ''

                    for key, value in recipe_dict.items():
                        if isinstance(value, float) and np.isnan(value):
                            recipe_dict[key] = None

                    category_picks.append({
                        'recipe_id': recipe_dict['RecipeId'],
                        'recipe_name': recipe_dict['Name'],
                        'image': recipe_dict['Images'],
                        'category': recipe_dict.get('RecipeCategory', '—'),
                        'rating': recipe_dict.get('AggregatedRating')
                    })
            else:
                category_picks = []
                selected_category = None
        else:
            category_picks = []
            selected_category = None
    else:
        category_picks = []
        selected_category = None

    # 3. Random Discoveries - get 6 random recipes (not in user's bookmarks)
    non_bookmarked_recipes = recipes_df_full[~recipes_df_full['RecipeId'].isin(all_bookmarked_ids)]

    if len(non_bookmarked_recipes) > 0:
        random_sample = non_bookmarked_recipes.sample(n=min(6, len(non_bookmarked_recipes)), random_state=42)

        random_discoveries = []
        for _, recipe in random_sample.iterrows():
            recipe_dict = recipe.to_dict()
            rid = recipe_dict.get('RecipeId')
            if rid:
                image_urls = image_collection.get_urls(rid)
                recipe_dict['Images'] = image_urls[0] if image_urls else ''

            for key, value in recipe_dict.items():
                if isinstance(value, float) and np.isnan(value):
                    recipe_dict[key] = None

            random_discoveries.append({
                'recipe_id': recipe_dict['RecipeId'],
                'recipe_name': recipe_dict['Name'],
                'image': recipe_dict['Images'],
                'category': recipe_dict.get('RecipeCategory', '—'),
                'rating': recipe_dict.get('AggregatedRating')
            })
    else:
        random_discoveries = []

    return jsonify({
        'from_bookmarks': from_bookmarks,
        'category_picks': category_picks,
        'category_name': selected_category,
        'random_discoveries': random_discoveries
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5678)

import pickle
import numpy as np
from flask import Flask, request, jsonify, render_template

from model.SpellChecker import SpellChecker ,spell_preprocessor
from model.CustomPreprocessor import CustomPreprocessor
from model.RecipeSearchEngine import RecipeSearchEngine
from model.ImageCollection import ImageCollection

app = Flask(__name__)

with open('resource/recipe_search_engine.pkl', 'rb') as f:
    search_engine = pickle.load(f)

with open('resource/image_collection.pkl', 'rb') as f:
    image_collection = pickle.load(f)

with open('resource/spell_collection.pkl', 'rb') as f:
    spell_checker = pickle.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower()
    return render_template('search.html', query=query)

@app.route('/api/search', methods=['GET'])
def api_search():
    query = request.args.get('q', '').lower()

    # Handle empty input
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

    # Search using BM25
    results_df = search_engine.search(query, top_k=10)

    # Debug: print columns to see what we're working with
    print("DataFrame columns:", results_df.columns.tolist())

    results = results_df.to_dict(orient='records')

    # Replace NaN values with None for JSON serialization
    for recipe in results:
        # Try different possible field names for the recipe ID
        recipe_id = recipe.get('RecipeId') or recipe.get('recipe_id') or recipe.get('Id') or recipe.get('id')

        if recipe_id:
            image_urls = image_collection.get_urls(recipe_id)
            recipe['Images'] = image_urls[0] if image_urls else ''
        else:
            recipe['Images'] = ''

        # Replace NaN values with None (becomes null in JSON)
        for key, value in recipe.items():
            if isinstance(value, float) and np.isnan(value):
                recipe[key] = None

    return jsonify({
        "original_query": query,
        "has_typo": has_typo,
        "suggested_query": suggested_query if has_typo else "",
        "results": results
    })

if __name__ == '__main__':
    app.run(debug=True, port=5678)
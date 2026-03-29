import numpy as np


class RecipeService:
    def __init__(self, search_engine, image_collection, recipes_df):
        self.search_engine = search_engine
        self.image_collection = image_collection
        self.recipes_df = recipes_df

    def search_recipes(self, query, spell_checker, top_k=10):
        if not query.strip():
            return None

        query_words = query.split()
        corrected_words = [spell_checker.correction(word) for word in query_words]
        has_typo = any(c != w for c, w in zip(corrected_words, query_words))
        suggested_query = " ".join(corrected_words)

        results_df = self.search_engine.search(suggested_query, top_k=top_k)
        results = results_df.to_dict(orient='records')

        for recipe in results:
            self._enrich_recipe(recipe)

        return {
            "original_query": query,
            "has_typo": has_typo,
            "suggested_query": suggested_query if has_typo else "",
            "results": results
        }

    def get_recipe_by_id(self, recipe_id):
        recipe_data = self.recipes_df[self.recipes_df['RecipeId'] == recipe_id]

        if recipe_data.empty:
            return None

        recipe = recipe_data.iloc[0].to_dict()
        self._enrich_recipe(recipe)
        return recipe

    def _enrich_recipe(self, recipe):
        rid = recipe.get('RecipeId') or recipe.get('recipe_id') or recipe.get('Id') or recipe.get('id')
        image_urls = self.image_collection.get_urls(rid) if rid else []
        recipe['Images'] = image_urls[0] if image_urls else ''

        for key, value in recipe.items():
            if isinstance(value, float) and np.isnan(value):
                recipe[key] = None

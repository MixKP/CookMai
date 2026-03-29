import random


class RecommendationService:
    def __init__(self, recipes_df, image_collection, recommendation_model, category_validator):
        self.recipes_df = recipes_df
        self.image_collection = image_collection
        self.recommendation_model = recommendation_model
        self.category_validator = category_validator

    def get_recommendations(self, user_id, bookmarks, selected_category=None):
        if not bookmarks:
            return {
                'from_bookmarks': [],
                'category_picks': [],
                'random_discoveries': []
            }

        from_bookmarks = self._get_from_bookmarks(bookmarks)
        all_bookmarked_ids = [b.recipe_id for b in bookmarks]

        category_picks, category_name = self._get_category_picks(
            selected_category,
            all_bookmarked_ids,
            bookmarks
        )

        random_discoveries = self._get_random_discoveries(all_bookmarked_ids)

        return {
            'from_bookmarks': from_bookmarks,
            'category_picks': category_picks,
            'category_name': category_name,
            'random_discoveries': random_discoveries
        }

    def _get_from_bookmarks(self, bookmarks):
        from_bookmarks_data = sorted(bookmarks, key=lambda x: x.user_rating or 0, reverse=True)[:6]
        result = []

        for b in from_bookmarks_data:
            recipe_data = self.recipes_df[self.recipes_df['RecipeId'] == b.recipe_id]
            if not recipe_data.empty:
                recipe = recipe_data.iloc[0].to_dict()
                self._enrich_recipe(recipe)
                result.append({
                    'recipe_id': recipe['RecipeId'],
                    'recipe_name': recipe['Name'],
                    'image': recipe['Images'],
                    'category': recipe.get('RecipeCategory', '—'),
                    'rating': recipe.get('AggregatedRating'),
                    'user_rating': b.user_rating,
                    'folder_name': b.folder.name if b.folder else 'Unknown'
                })
        return result

    def _get_category_picks(self, selected_category, all_bookmarked_ids, bookmarks):
        bookmarked_recipes = self.recipes_df[self.recipes_df['RecipeId'].isin(all_bookmarked_ids)]

        if selected_category:
            return self._get_selected_category_picks(selected_category, all_bookmarked_ids)
        elif not bookmarked_recipes.empty:
            return self._get_random_category_picks(bookmarked_recipes, all_bookmarked_ids)
        else:
            return [], None

    def _get_selected_category_picks(self, selected_category, all_bookmarked_ids):
        category_recipes = self.recipes_df[
            (self.recipes_df['RecipeCategory'] == selected_category) &
            (~self.recipes_df['RecipeId'].isin(all_bookmarked_ids))
        ]

        if len(category_recipes) > 0:
            category_sample = category_recipes.sample(n=min(6, len(category_recipes)), random_state=42)
            return self._process_recipe_sample(category_sample), selected_category
        else:
            return [], None

    def _get_random_category_picks(self, bookmarked_recipes, all_bookmarked_ids):
        categories = bookmarked_recipes['RecipeCategory'].dropna().unique().tolist()
        categories = [c for c in categories if self.category_validator.is_valid(c)]

        if not categories:
            return [], None

        selected_category = random.choice(categories)
        category_recipes = self.recipes_df[
            (self.recipes_df['RecipeCategory'] == selected_category) &
            (~self.recipes_df['RecipeId'].isin(all_bookmarked_ids))
        ]

        if len(category_recipes) > 0:
            category_sample = category_recipes.sample(n=min(6, len(category_recipes)), random_state=42)
            return self._process_recipe_sample(category_sample), selected_category
        else:
            return [], None

    def _get_random_discoveries(self, all_bookmarked_ids):
        non_bookmarked_recipes = self.recipes_df[~self.recipes_df['RecipeId'].isin(all_bookmarked_ids)]

        if len(non_bookmarked_recipes) > 0:
            random_sample = non_bookmarked_recipes.sample(n=min(6, len(non_bookmarked_recipes)), random_state=42)
            return self._process_recipe_sample(random_sample)
        else:
            return []

    def _process_recipe_sample(self, recipes_df):
        result = []
        for _, recipe in recipes_df.iterrows():
            recipe_dict = recipe.to_dict()
            self._enrich_recipe(recipe_dict)
            result.append({
                'recipe_id': recipe_dict['RecipeId'],
                'recipe_name': recipe_dict['Name'],
                'image': recipe_dict['Images'],
                'category': recipe_dict.get('RecipeCategory', '—'),
                'rating': recipe_dict.get('AggregatedRating')
            })
        return result

    def get_folder_suggestions(self, folder_id, user_id, bookmarks):
        if not bookmarks:
            return None

        folder_recipe_ids = [b.recipe_id for b in bookmarks]
        recommendations = self.recommendation_model.get_folder_recommendations(folder_recipe_ids, top_k=12)

        if not recommendations:
            return None

        for recipe in recommendations:
            image_urls = self.image_collection.get_urls(recipe['recipe_id'])
            recipe['image'] = image_urls[0] if image_urls else ''

        return recommendations

    def _enrich_recipe(self, recipe):
        import numpy as np
        rid = recipe.get('RecipeId') or recipe.get('recipe_id') or recipe.get('Id') or recipe.get('id')
        image_urls = self.image_collection.get_urls(rid) if rid else []
        recipe['Images'] = image_urls[0] if image_urls else ''

        for key, value in recipe.items():
            if isinstance(value, float) and np.isnan(value):
                recipe[key] = None

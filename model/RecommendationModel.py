import numpy as np
import pandas as pd
import pickle
import re
import string
from sklearn.preprocessing import MinMaxScaler


class RecommendationModel:
    def __init__(self, model_path, recipes_path):
        print("Loading ML recommendation model...")

        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.tfidf = model_data['tfidf']
        self.lsa = model_data['lsa']
        self.count_vec = model_data['count_vec']
        self.lda = model_data['lda']
        self.X_final = model_data['X_final']

        with open(recipes_path, 'rb') as f:
            recipes_full = pickle.load(f)

        self.recipes = self._process_recipes(recipes_full)
        print(f"ML model loaded with {len(self.recipes)} recipes")

    def _process_recipes(self, recipes_full):
        recipes = recipes_full.copy()

        recipes["text"] = (
            recipes["Name"].fillna('') + " " +
            recipes["RecipeIngredientParts"].fillna('') + " " +
            recipes["RecipeInstructions"].fillna('')
        )

        recipes = recipes.dropna(subset=["AggregatedRating"]).reset_index(drop=True)

        def preprocess(text):
            text = text.lower()
            text = text.translate(str.maketrans('', '', string.punctuation))
            text = re.sub(r'\d+', '', text)
            return text

        recipes["clean_text"] = recipes["text"].apply(preprocess)

        return recipes

    def get_folder_recommendations(self, folder_recipe_ids, top_k=10):
        folder_recipes = self.recipes[self.recipes['RecipeId'].isin(folder_recipe_ids)]

        if len(folder_recipes) == 0:
            return []

        folder_indices = folder_recipes.index.tolist()

        user_profile = self.X_final[folder_indices].mean(axis=0)

        if isinstance(user_profile, np.matrix):
            user_profile = user_profile.A
        similarity_scores = np.asarray(self.X_final @ user_profile.T).flatten()

        import sklearn
        import warnings

        if sklearn.__version__.startswith('1.8'):
            from sklearn.utils.validation import check_array as original_check_array
            import functools

            def patched_check_array(*args, **kwargs):
                if 'force_all_finite' in kwargs:
                    kwargs['ensure_all_finite'] = kwargs.pop('force_all_finite')
                return original_check_array(*args, **kwargs)

            sklearn.utils.validation.check_array = patched_check_array

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                predicted_ratings = self.model.predict(self.X_final)
        finally:
            if sklearn.__version__.startswith('1.8'):
                sklearn.utils.validation.check_array = original_check_array

        scaler = MinMaxScaler()
        normalized_similarity = scaler.fit_transform(similarity_scores.reshape(-1, 1)).flatten()
        normalized_ratings = scaler.fit_transform(predicted_ratings.reshape(-1, 1)).flatten()

        final_scores = (normalized_similarity * 0.7) + (normalized_ratings * 0.3)

        self.recipes['recommendation_score'] = final_scores

        recommendations = self.recipes[~self.recipes['RecipeId'].isin(folder_recipe_ids)]
        recommendations = recommendations.sort_values('recommendation_score', ascending=False)
        top_recommendations = recommendations.head(top_k)

        result = []
        for _, recipe in top_recommendations.iterrows():
            result.append({
                'recipe_id': int(recipe['RecipeId']),
                'recipe_name': recipe['Name'],
                'category': recipe.get('RecipeCategory', '—'),
                'rating': float(recipe['AggregatedRating']) if pd.notna(recipe['AggregatedRating']) else None,
                'recommendation_score': float(recipe['recommendation_score'])
            })

        return result

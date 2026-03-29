"""
ML-based Recommendation Model for UC-008
Uses LightGBM + TF-IDF + LSA + LDA to generate personalized recommendations
"""
import numpy as np
import pandas as pd
import pickle
import re
import string
from sklearn.preprocessing import MinMaxScaler


class RecommendationModel:
    def __init__(self, model_path, recipes_path):
        """
        Load the trained model and prepare the recipes dataset.

        Args:
            model_path: Path to recipe_recommendation_model.pkl
            recipes_path: Path to recipes.pkl
        """
        print("Loading ML recommendation model...")

        # Load model components
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.tfidf = model_data['tfidf']
        self.lsa = model_data['lsa']
        self.count_vec = model_data['count_vec']
        self.lda = model_data['lda']
        self.X_final = model_data['X_final']

        # Load and process recipes to match training
        with open(recipes_path, 'rb') as f:
            recipes_full = pickle.load(f)

        self.recipes = self._process_recipes(recipes_full)
        print(f"ML model loaded with {len(self.recipes)} recipes")

    def _process_recipes(self, recipes_full):
        """
        Process recipes exactly as done during training.
        This ensures alignment between X_final rows and recipe data.
        """
        recipes = recipes_full.copy()

        # Create text field (same as notebook)
        recipes["text"] = (
            recipes["Name"].fillna('') + " " +
            recipes["RecipeIngredientParts"].fillna('') + " " +
            recipes["RecipeInstructions"].fillna('')
        )

        # Drop recipes without ratings (same as notebook)
        recipes = recipes.dropna(subset=["AggregatedRating"]).reset_index(drop=True)

        # Preprocess text (same as notebook)
        def preprocess(text):
            text = text.lower()
            text = text.translate(str.maketrans('', '', string.punctuation))
            text = re.sub(r'\d+', '', text)
            return text

        recipes["clean_text"] = recipes["text"].apply(preprocess)

        return recipes

    def get_folder_recommendations(self, folder_recipe_ids, top_k=10):
        """
        Generate ML-powered recommendations for a specific folder.

        Args:
            folder_recipe_ids: List of RecipeId values in the folder
            top_k: Number of recommendations to return

        Returns:
            List of dicts with recommended recipe details
        """
        # Find indices of folder recipes in the processed dataset
        folder_recipes = self.recipes[self.recipes['RecipeId'].isin(folder_recipe_ids)]

        if len(folder_recipes) == 0:
            return []

        folder_indices = folder_recipes.index.tolist()

        # Build user profile from folder recipes (average of their feature vectors)
        user_profile = self.X_final[folder_indices].mean(axis=0)

        # Calculate content similarity scores
        if isinstance(user_profile, np.matrix):
            user_profile = user_profile.A  # Convert matrix to array if needed
        similarity_scores = np.asarray(self.X_final @ user_profile.T).flatten()

        # Get predicted ratings from ML model
        # Handle sklearn version compatibility (force_all_finite renamed to ensure_all_finite in 1.8.0)
        import sklearn
        import warnings

        # Monkey patch for sklearn 1.8.0 compatibility
        if sklearn.__version__.startswith('1.8'):
            from sklearn.utils import __all__ as sklearn_utils_all
            from sklearn.utils.validation import check_array as original_check_array
            import functools

            def patched_check_array(*args, **kwargs):
                # Rename force_all_finite to ensure_all_finite
                if 'force_all_finite' in kwargs:
                    kwargs['ensure_all_finite'] = kwargs.pop('force_all_finite')
                return original_check_array(*args, **kwargs)

            # Temporarily patch
            sklearn.utils.validation.check_array = patched_check_array

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                predicted_ratings = self.model.predict(self.X_final)
        finally:
            # Restore original function if we patched it
            if sklearn.__version__.startswith('1.8'):
                sklearn.utils.validation.check_array = original_check_array

        # Normalize both scores to 0-1 range
        scaler = MinMaxScaler()
        normalized_similarity = scaler.fit_transform(similarity_scores.reshape(-1, 1)).flatten()
        normalized_ratings = scaler.fit_transform(predicted_ratings.reshape(-1, 1)).flatten()

        # Combine: 70% content similarity + 30% predicted ratings
        final_scores = (normalized_similarity * 0.7) + (normalized_ratings * 0.3)

        # Add scores to recipes DataFrame
        self.recipes['recommendation_score'] = final_scores
        self.recipes['similarity_score'] = normalized_similarity
        self.recipes['predicted_rating_score'] = normalized_ratings

        # Filter out folder's own recipes
        recommendations = self.recipes[~self.recipes['RecipeId'].isin(folder_recipe_ids)]

        # Sort by final score and return top_k
        recommendations = recommendations.sort_values('recommendation_score', ascending=False)
        top_recommendations = recommendations.head(top_k)

        # Convert to list of dicts for API response
        result = []
        for _, recipe in top_recommendations.iterrows():
            result.append({
                'recipe_id': int(recipe['RecipeId']),
                'recipe_name': recipe['Name'],
                'category': recipe.get('RecipeCategory', '—'),
                'rating': float(recipe['AggregatedRating']) if pd.notna(recipe['AggregatedRating']) else None,
                'recommendation_score': float(recipe['recommendation_score']),
                'similarity_score': float(recipe['similarity_score']),  # Evidence: content similarity
                'predicted_rating_score': float(recipe['predicted_rating_score']),  # Evidence: ML prediction
                'description': recipe.get('Description', '')
            })

        return result

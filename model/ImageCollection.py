class ImageCollection:
    def __init__(self, image_dataframe):
        self.collection = image_dataframe.set_index('RecipeId')
        
    def get_urls(self, recipe_id):
        try:
            result = self.collection.loc[recipe_id, 'Images']
            
            if isinstance(result, str):
                return [result]
            
            return result.tolist()
        except KeyError:
            return []
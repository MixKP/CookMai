from model.User import db, Bookmark, Folder


class BookmarkService:
    def __init__(self, timezone_converter):
        self.timezone_converter = timezone_converter

    def add_bookmark(self, user_id, folder_id, recipe_id, recipe_name, user_rating, notes):
        if not folder_id or not recipe_id or not recipe_name:
            raise ValueError("folder_id, recipe_id, and recipe_name are required")

        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            raise ValueError("Folder not found")

        existing = Bookmark.query.filter_by(
            user_id=user_id,
            folder_id=folder_id,
            recipe_id=recipe_id
        ).first()

        if existing:
            raise ValueError("Recipe already bookmarked in this folder")

        bookmark = Bookmark(
            user_id=user_id,
            folder_id=folder_id,
            recipe_id=recipe_id,
            recipe_name=recipe_name,
            user_rating=user_rating if user_rating is not None else None,
            notes=notes or None
        )
        db.session.add(bookmark)
        db.session.commit()
        return bookmark

    def delete_bookmark(self, bookmark_id, user_id):
        bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=user_id).first()
        if not bookmark:
            return False

        db.session.delete(bookmark)
        db.session.commit()
        return True

    def get_folder_bookmarks(self, folder_id, user_id):
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            return None

        bookmarks = Bookmark.query.filter_by(folder_id=folder_id)\
            .order_by(Bookmark.user_rating.desc(), Bookmark.recipe_name.asc()).all()
        return bookmarks

    def get_all_bookmarks(self, user_id):
        return Bookmark.query.filter_by(user_id=user_id).all()

    def bookmark_to_dict(self, bookmark):
        return {
            'id': bookmark.id,
            'recipe_id': bookmark.recipe_id,
            'recipe_name': bookmark.recipe_name,
            'user_rating': bookmark.user_rating,
            'notes': bookmark.notes,
            'created_at': self.timezone_converter(bookmark.created_at).isoformat() if bookmark.created_at else None
        }

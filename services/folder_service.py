from model.User import db, Folder, Bookmark


class FolderService:
    def __init__(self, timezone_converter):
        self.timezone_converter = timezone_converter

    def create_folder(self, user_id, name, description, icon):
        if not name:
            raise ValueError("Folder name is required")
        if len(name) > 100:
            raise ValueError("Folder name must be less than 100 characters")

        folder = Folder(
            user_id=user_id,
            name=name,
            description=description or None,
            icon=icon
        )
        db.session.add(folder)
        db.session.commit()
        return folder

    def update_folder(self, folder_id, user_id, name, description, icon):
        if not name:
            raise ValueError("Folder name is required")
        if len(name) > 100:
            raise ValueError("Folder name must be less than 100 characters")

        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            return None

        folder.name = name
        folder.description = description or None
        folder.icon = icon
        db.session.commit()
        return folder

    def delete_folder(self, folder_id, user_id):
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            return False

        db.session.delete(folder)
        db.session.commit()
        return True

    def get_user_folders(self, user_id):
        return Folder.query.filter_by(user_id=user_id).order_by(Folder.created_at.desc()).all()

    def get_folder_by_id(self, folder_id, user_id):
        return Folder.query.filter_by(id=folder_id, user_id=user_id).first()

    def folder_to_dict(self, folder):
        return {
            'id': folder.id,
            'name': folder.name,
            'description': folder.description,
            'icon': folder.icon,
            'bookmark_count': len(folder.bookmarks),
            'created_at': self.timezone_converter(folder.created_at).isoformat() if folder.created_at else None
        }

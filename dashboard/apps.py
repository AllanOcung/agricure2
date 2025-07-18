from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    
    def ready(self):
        """Initialize app when Django starts"""
        try:
            # Import and run initialization
            from .utils import ensure_media_directories
            ensure_media_directories()
        except Exception as e:
            print(f"Warning: Could not initialize media directories: {e}")

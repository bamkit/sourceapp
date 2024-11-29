from django.apps import AppConfig

class PlannerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'planner'

    def ready(self):
        # Create temp_sequences directory if it doesn't exist
        import os
        from django.conf import settings
        if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'temp_sequences')):
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'temp_sequences'))

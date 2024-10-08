from django.apps import AppConfig
from django.conf import settings
import os

class PlannerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'planner'

    def ready(self):
        if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'temp_sequences')):
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'temp_sequences'))

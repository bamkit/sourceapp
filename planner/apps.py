# from django.apps import AppConfig
# from django.conf import settings
# import os

# class PlannerConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'planner'

#     def ready(self):
#         if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'temp_sequences')):
#             os.makedirs(os.path.join(settings.MEDIA_ROOT, 'temp_sequences'))

# planner/apps.py

from django.apps import AppConfig
import threading

class PlannerConfig(AppConfig):
    name = 'planner'

    def ready(self):
        # Start the background task when the app is ready
        from django.core.management import call_command

        def start_background_tasks():
            try:
                call_command('process_tasks')  # This will run the background tasks
            except Exception as e:
                print(f"Error in background task: {e}")

        # Start the background task in a separate thread
        threading.Thread(target=start_background_tasks, daemon=True).start()

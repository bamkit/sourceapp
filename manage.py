#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'obn_app.settings')
    try:
        from django.core.management import execute_from_command_line, call_command
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Check if the command is runserver before starting background tasks
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        try:
            # Run the background task directly
            call_command('process_tasks')
        except Exception as e:
            print(f"Error in background task: {e}")

    # Execute Django commands (including runserver)
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

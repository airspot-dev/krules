#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from dotenv import load_dotenv

load_dotenv("../.env.local")  # for KRULES_REPO_DIR

sys.path.append("..")
sys.path.append(os.path.join("..", "apps", "krules-djangoapps-common"))
sys.path.append(os.path.join("..", "apps", "krules-djangoapps-procevents"))
sys.path.append(os.path.join("..", "apps", "krules-djangoapps-scheduler"))

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_dev.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
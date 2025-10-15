import os
import sys
from pathlib import Path

# Add the repo root (two levels up from this file) to Python path
# This makes "backend.backend.settings" importable no matter what cwd is.
BASE_DIR = Path(__file__).resolve().parents[1]   # points to outer backend/
sys.path.append(str(BASE_DIR))                   # adds outer backend/ to PYTHONPATH

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.backend.settings')

application = get_wsgi_application()

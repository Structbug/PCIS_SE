"""Explicit Django settings-module selection (H-10).

A server must never silently boot the DEBUG=True development settings because
someone forgot to set DJANGO_SETTINGS_MODULE. This module:

1. prefers the process environment (already set DJANGO_SETTINGS_MODULE),
2. otherwise loads it from the checkout's local ``.env`` file if present
   (keeps the README dev workflow working without exports),
3. otherwise **fails loudly** with instructions instead of guessing.

The `--settings` manage.py flag is honoured by returning an empty string so
Django's own argument parsing can read it.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


def resolve_settings_module():
    """Return the explicit settings module, or exit loudly if none is given."""
    if "--settings" in sys.argv:
        return os.environ.get("DJANGO_SETTINGS_MODULE", "")
    _load_env_file(ENV_FILE)
    module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if module:
        return module
    sys.stderr.write(
        "DJANGO_SETTINGS_MODULE is not set - refusing to guess a default "
        "(H-10). Set it explicitly to opt in:\n"
        "  config.settings.dev   local development (DEBUG=True)\n"
        "  config.settings.test  isolated SQLite test suite\n"
        "  config.settings.prod  production (DEBUG=False)\n"
        "  e.g. DJANGO_SETTINGS_MODULE=config.settings.prod\n"
    )
    sys.exit(1)
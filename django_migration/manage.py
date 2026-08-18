#!/usr/bin/env python3
import os
import sys

from config.load_settings import resolve_settings_module


def main():
    module = resolve_settings_module()
    if module:
        os.environ["DJANGO_SETTINGS_MODULE"] = module
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inventory.models import ActivityLog


class Command(BaseCommand):
    help = (
        "Delete activity logs older than a retention period so the table "
        "stays bounded in size."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=getattr(settings, "ACTIVITY_LOG_RETENTION_DAYS", 90),
            help="Delete logs older than this many days (default: 90).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days < 1:
            self.stderr.write(self.style.ERROR("--days must be at least 1"))
            return
        cutoff = timezone.now() - timedelta(days=days)
        count, _ = ActivityLog.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} activity log(s) older than {days} day(s)"
            )
        )

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import Department, Floor, RoomType, Room


def _normalize(name: str) -> str:
    return name.strip().casefold()


class Command(BaseCommand):
    help = "Merge duplicate department rows into a canonical department name. Dry-run by default. Use --apply to perform changes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the merge. Without this flag the command only prints what it would do.",
        )
        parser.add_argument(
            "--canonical",
            default="Electronics and Computer Engineering",
            help="Canonical department name to merge into (default: Electronics and Computer Engineering)",
        )
        parser.add_argument(
            "--duplicates",
            nargs="*",
            default=["Department of Computer and Electronics engineering"],
            help="List of department names to merge into canonical (space separated)",
        )

    def handle(self, *args, **options):
        apply_changes = options.get("apply")
        canonical_name = options.get("canonical")
        duplicates = options.get("duplicates") or []

        canonical_normalized = _normalize(canonical_name)
        duplicate_normalized = {_normalize(n): n for n in duplicates}

        # Ensure canonical exists (create if necessary) but don't touch isActive flag if present
        canonical = Department.objects.filter(departmentNameNormalized=canonical_normalized).first()
        if not canonical:
            self.stdout.write(f"Canonical department not found. Creating: '{canonical_name}'")
            if apply_changes:
                canonical = Department.objects.create(
                    departmentName=canonical_name,
                    departmentNameNormalized=canonical_normalized,
                )
                self.stdout.write(f"Created canonical department with id {canonical.pk}")
            else:
                self.stdout.write("Dry-run: would create canonical department")

        else:
            self.stdout.write(f"Found canonical department id={canonical.pk} name='{canonical.departmentName}'")

        # Find all departments matching duplicate normalized names (and any other variants colliding with canonical)
        # We'll also look for departments whose normalized value equals any duplicate or where normalized equals canonical but name differs
        candidates = Department.objects.filter(isActive=True)
        to_merge = []
        for dept in candidates:
            nm = _normalize(dept.departmentName or "")
            if nm in duplicate_normalized and dept.pk != (canonical.pk if canonical else None):
                to_merge.append(dept)
            # also merge variants that equal canonical normalized but different display name
            elif nm == canonical_normalized and (dept.departmentName or "").strip() != canonical_name.strip() and dept.pk != (canonical.pk if canonical else None):
                to_merge.append(dept)

        if not to_merge:
            self.stdout.write("No duplicate departments found to merge.")
            return

        self.stdout.write(f"Found {len(to_merge)} departments to merge into canonical '{canonical_name}':")
        for d in to_merge:
            self.stdout.write(f" - id={d.pk} name='{d.departmentName}' normalized='{d.departmentNameNormalized}'")

        if not apply_changes:
            self.stdout.write("")
            self.stdout.write("Dry-run complete. Run with --apply to perform the merge.")
            return

        # Perform the merge in a transaction
        with transaction.atomic():
            if not canonical:
                canonical = Department.objects.get(departmentNameNormalized=canonical_normalized)
            for dup in to_merge:
                self.stdout.write(f"Repointing references from {dup.pk} -> {canonical.pk}")
                # Update FK references on dependent models
                Floor.objects.filter(department_id=dup.pk).update(department_id=canonical.pk)
                RoomType.objects.filter(department_id=dup.pk).update(department_id=canonical.pk)
                # Mark duplicate inactive and normalize
                dup.isActive = False
                dup.departmentNameNormalized = _normalize(dup.departmentName or "")
                dup.save(update_fields=["isActive", "departmentNameNormalized", "updated_at"]) 
                self.stdout.write(f"Deactivated duplicate department id={dup.pk}")

        self.stdout.write("Merge completed successfully.")

from django.db import migrations, models


def add_postgres_trigram_indexes(apps, schema_editor):
    """Provide indexed case-insensitive substring search in PostgreSQL.

    SQLite development databases continue to work without these optional
    PostgreSQL indexes. `icontains` compiles to `UPPER(column) LIKE ...`, so
    the indexes intentionally use the same expression.
    """
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cursor.execute(
            'CREATE INDEX items_name_trgm_idx ON items '
            'USING GIN (UPPER("itemName") gin_trgm_ops)'
        )
        cursor.execute(
            'CREATE INDEX items_serial_trgm_idx ON items '
            'USING GIN (UPPER("itemSerialNumber") gin_trgm_ops)'
        )


def remove_postgres_trigram_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS items_name_trgm_idx")
        cursor.execute("DROP INDEX IF EXISTS items_serial_trgm_idx")


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0009_room_roomno"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="item",
            name="items_updated_109f6f_idx",
        ),
        migrations.AddIndex(
            model_name="item",
            index=models.Index(
                fields=["isActive", "-updated_at", "-id"],
                name="item_active_updated_id_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="item",
            index=models.Index(
                fields=["isActive", "itemFloor", "itemRoom"],
                name="item_active_floor_room_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="item",
            index=models.Index(
                fields=["isActive", "itemStatus", "itemSource"],
                name="item_active_status_source_idx",
            ),
        ),
        migrations.RunPython(add_postgres_trigram_indexes, remove_postgres_trigram_indexes),
    ]

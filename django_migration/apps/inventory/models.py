from django.db import models
from secrets import token_hex

from apps.accounts.models import User


def generate_object_id():
    return token_hex(12)


class Floor(models.Model):
    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    floorName = models.TextField()
    # Nullable only to retain access to reference data created before departments
    # were introduced. New records created through the API are department scoped.
    department = models.ForeignKey(
        "Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="floors"
    )
    createdBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="floors"
    )
    isActive = models.BooleanField(default=True, db_column="isActive")
    floorNameNormalized = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "floors"


class RoomType(models.Model):
    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    roomTypeName = models.TextField()
    department = models.ForeignKey(
        "Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="room_types"
    )
    createdBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="room_types"
    )
    isActive = models.BooleanField(default=True, db_column="isActive")
    roomTypeNameNormalized = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roomtypes"


class Department(models.Model):
    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    departmentName = models.TextField()
    createdBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="departments"
    )
    isActive = models.BooleanField(default=True, db_column="isActive")
    departmentNameNormalized = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "departments"


class Category(models.Model):
    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    categoryName = models.TextField()
    createdBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="categories"
    )
    isActive = models.BooleanField(default=True, db_column="isActive")
    categoryNameNormalized = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"


class SubCategory(models.Model):
    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    subCategoryName = models.TextField()
    subCategoryAbbreviation = models.TextField(null=True, blank=True)
    isActive = models.BooleanField(default=True, db_column="isActive")
    createdBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_categories"
    )
    lastItemSerialNumber = models.IntegerField(default=0)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_categories"
    )
    subCategoryNameNormalized = models.TextField(null=True, blank=True)
    subCategoryAbbreviationNormalized = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subcategories"


class Room(models.Model):
    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    roomName = models.TextField()
    roomNo = models.TextField(null=True, blank=True)
    floor = models.ForeignKey(
        Floor, on_delete=models.SET_NULL, null=True, blank=True, related_name="rooms"
    )
    roomType = models.ForeignKey(
        RoomType, on_delete=models.SET_NULL, null=True, blank=True, related_name="rooms"
    )
    allottedTo = models.TextField(null=True, blank=True)
    createdBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rooms"
    )
    isActive = models.BooleanField(default=True, db_column="isActive")
    roomNameNormalized = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rooms"


class Item(models.Model):
    class Status(models.TextChoices):
        WORKING = "Working", "Working"
        REPAIRABLE = "Repairable", "Repairable"
        NOT_WORKING = "Not working", "Not working"

    class Source(models.TextChoices):
        PURCHASE = "Purchase", "Purchase"
        DONATION = "Donation", "Donation"

    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    itemName = models.TextField()
    itemCategory = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="items", null=True, blank=True
    )
    itemSubCategory = models.ForeignKey(
        SubCategory, on_delete=models.PROTECT, related_name="items", null=True, blank=True
    )
    itemModelNumberOrMake = models.TextField(null=True, blank=True)
    itemAcquiredDate = models.DateField(null=True, blank=True)
    itemCost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    itemFloor = models.ForeignKey(
        Floor, on_delete=models.PROTECT, related_name="items"
    )
    itemRoom = models.ForeignKey(
        Room, on_delete=models.PROTECT, related_name="items"
    )
    itemStatus = models.TextField(choices=Status.choices)
    itemSource = models.TextField(choices=Source.choices)
    itemDescription = models.TextField(null=True, blank=True)
    itemSerialNumber = models.TextField(default="0")
    isActive = models.BooleanField(default=True, db_column="isActive")
    deactivatedAt = models.DateTimeField(null=True, blank=True)
    itemRemark = models.TextField(null=True, blank=True)
    createdBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "items"
        indexes = [
            # Matches the active inventory listing and cursor ordering.
            models.Index(fields=["isActive", "-updated_at", "-id"], name="item_active_updated_id_idx"),
            # Speeds the structured filters that can be combined with search.
            models.Index(fields=["isActive", "itemFloor", "itemRoom"], name="item_active_floor_room_idx"),
            models.Index(fields=["isActive", "itemStatus", "itemSource"], name="item_active_status_source_idx"),
        ]


class ActivityLog(models.Model):
    class EntityType(models.TextChoices):
        ITEM = "Item", "Item"
        USER = "User", "User"
        ROOM = "Room", "Room"
        CATEGORY = "Category", "Category"
        FLOOR = "Floor", "Floor"
        DEPARTMENT = "Department", "Department"
        ROOMTYPE = "Roomtype", "Roomtype"
        SUBCATEGORY = "SubCategory", "SubCategory"

    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    action = models.TextField()
    entityType = models.TextField(choices=EntityType.choices)
    entityId = models.CharField(max_length=24, null=True, blank=True)
    entityName = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    performedByName = models.TextField(null=True, blank=True)
    performedByRole = models.TextField(null=True, blank=True)
    performedBy = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs"
    )
    changes = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activitylogs"
        ordering = ["-created_at"]

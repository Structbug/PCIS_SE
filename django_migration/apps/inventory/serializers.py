from rest_framework import serializers
from .models import ActivityLog, Category, Department, Floor, Item, Room, RoomType, SubCategory


class DepartmentSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Department
        fields = ("_id", "departmentName", "createdBy", "isActive", "createdAt", "updatedAt")


class DepartmentListSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)

    class Meta:
        model = Department
        fields = ("_id", "departmentName")


class FloorSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(read_only=True)
    departmentId = serializers.CharField(source="department_id", read_only=True, allow_null=True)
    departmentName = serializers.CharField(source="department.departmentName", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Floor
        fields = (
            "_id", "floorName", "departmentId", "departmentName", "createdBy", "isActive",
            "createdAt", "updatedAt",
        )


class FloorListSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    departmentId = serializers.CharField(source="department_id", read_only=True, allow_null=True)
    departmentName = serializers.CharField(source="department.departmentName", read_only=True, allow_null=True)

    class Meta:
        model = Floor
        fields = ("_id", "floorName", "departmentId", "departmentName")


class RoomTypeSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(read_only=True)
    departmentId = serializers.CharField(source="department_id", read_only=True, allow_null=True)
    departmentName = serializers.CharField(source="department.departmentName", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = RoomType
        fields = (
            "_id", "roomTypeName", "departmentId", "departmentName", "createdBy", "isActive",
            "createdAt", "updatedAt",
        )


class RoomTypeListSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    departmentId = serializers.CharField(source="department_id", read_only=True, allow_null=True)
    departmentName = serializers.CharField(source="department.departmentName", read_only=True, allow_null=True)

    class Meta:
        model = RoomType
        fields = ("_id", "roomTypeName", "departmentId", "departmentName")


class CategorySerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Category
        fields = (
            "_id", "categoryName", "createdBy", "isActive",
            "createdAt", "updatedAt",
        )


class CategoryListSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)

    class Meta:
        model = Category
        fields = ("_id", "categoryName")


class CategoryDescriptionSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    creatorUsername = serializers.CharField(source="createdBy.username", read_only=True, allow_null=True)
    totalItems = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Category
        fields = (
            "_id", "categoryName", "totalItems", "creatorUsername",
            "createdAt", "updatedAt",
        )

    def get_totalItems(self, obj):
        return obj.items_count if hasattr(obj, "items_count") else 0


class SubCategorySerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(read_only=True)
    category = serializers.CharField(source="category_id", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = SubCategory
        fields = (
            "_id", "subCategoryName", "subCategoryAbbreviation", "isActive",
            "createdBy", "lastItemSerialNumber", "category",
            "createdAt", "updatedAt",
        )


class SubCategoryListSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)

    class Meta:
        model = SubCategory
        fields = ("_id", "subCategoryName")


class SubCategoryDescriptionSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    creatorUsername = serializers.CharField(source="createdBy.username", read_only=True, allow_null=True)
    totalItems = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = SubCategory
        fields = (
            "_id", "subCategoryName", "subCategoryAbbreviation",
            "totalItems", "creatorUsername", "createdAt", "updatedAt",
        )

    def get_totalItems(self, obj):
        return obj.items_count if hasattr(obj, "items_count") else 0


class RoomSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(read_only=True)
    floor = serializers.CharField(source="floor_id", read_only=True, allow_null=True)
    roomType = serializers.CharField(source="roomType_id", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Room
        fields = (
            "_id", "roomName", "roomNo", "floor", "roomType", "allottedTo",
            "createdBy", "isActive", "createdAt", "updatedAt",
        )


class RoomReportSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    roomFloorId = serializers.CharField(source="floor_id", read_only=True, allow_null=True)
    roomFloorName = serializers.CharField(source="floor.floorName", read_only=True, allow_null=True)
    departmentId = serializers.CharField(source="floor.department_id", read_only=True, allow_null=True)
    departmentName = serializers.CharField(source="floor.department.departmentName", read_only=True, allow_null=True)
    roomTypeId = serializers.CharField(source="roomType_id", read_only=True, allow_null=True)
    roomTypeName = serializers.CharField(source="roomType.roomTypeName", read_only=True, allow_null=True)
    creatorUsername = serializers.CharField(source="createdBy.username", read_only=True, allow_null=True)
    totalItems = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Room
        fields = (
            "_id", "roomName", "roomNo", "totalItems", "roomFloorId", "roomFloorName", "departmentId", "departmentName",
            "roomTypeId", "roomTypeName", "creatorUsername", "allottedTo",
            "createdAt", "updatedAt",
        )

    def get_totalItems(self, obj):
        return obj.items_count if hasattr(obj, "items_count") else 0


class RoomNameListSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    floorName = serializers.CharField(source="floor.floorName", read_only=True, allow_null=True)
    departmentName = serializers.CharField(source="floor.department.departmentName", read_only=True, allow_null=True)

    class Meta:
        model = Room
        fields = ("_id", "roomName", "roomNo", "floorName", "departmentName")


class ItemSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(read_only=True)
    itemCategory = serializers.CharField(source="itemCategory_id", read_only=True, allow_null=True)
    itemSubCategory = serializers.CharField(source="itemSubCategory_id", read_only=True, allow_null=True)
    itemFloor = serializers.CharField(source="itemFloor_id", read_only=True)
    itemRoom = serializers.CharField(source="itemRoom_id", read_only=True)
    itemCost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Item
        fields = (
            "_id", "itemName", "itemCategory", "itemSubCategory",
            "itemModelNumberOrMake", "itemAcquiredDate", "itemCost",
            "itemFloor", "itemRoom", "itemStatus", "itemSource",
            "itemDescription", "itemSerialNumber", "isActive",
            "deactivatedAt", "itemRemark", "createdBy",
            "createdAt", "updatedAt",
        )


class ItemReportSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    itemCategory = serializers.CharField(source="itemCategory_id", read_only=True, allow_null=True)
    itemSubCategory = serializers.CharField(source="itemSubCategory_id", read_only=True, allow_null=True)
    itemFloor = serializers.CharField(source="itemFloor_id", read_only=True)
    itemRoom = serializers.CharField(source="itemRoom_id", read_only=True)
    createdBy = serializers.CharField(source="createdBy_id", read_only=True, allow_null=True)
    categoryName = serializers.CharField(source="itemCategory.categoryName", read_only=True, allow_null=True)
    subCategoryName = serializers.CharField(source="itemSubCategory.subCategoryName", read_only=True, allow_null=True)
    floorName = serializers.CharField(source="itemFloor.floorName", read_only=True, allow_null=True)
    departmentId = serializers.CharField(source="itemFloor.department_id", read_only=True, allow_null=True)
    departmentName = serializers.CharField(source="itemFloor.department.departmentName", read_only=True, allow_null=True)
    roomName = serializers.CharField(source="itemRoom.roomName", read_only=True, allow_null=True)
    creatorUsername = serializers.CharField(source="createdBy.username", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Item
        fields = (
            "_id", "itemName", "itemCategory", "itemSubCategory",
            "itemModelNumberOrMake", "itemAcquiredDate", "itemCost",
            "itemFloor", "itemRoom", "itemStatus", "itemSource",
            "itemDescription", "itemSerialNumber", "isActive",
            "deactivatedAt", "itemRemark", "createdBy",
            "categoryName", "subCategoryName", "floorName", "departmentId", "departmentName", "roomName",
            "creatorUsername", "createdAt", "updatedAt",
        )


class ActivityLogSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)

    class Meta:
        model = ActivityLog
        fields = (
            "_id", "action", "entityType", "entityId", "entityName",
            "description", "performedByName", "performedByRole",
            "performedBy", "changes", "created_at",
        )

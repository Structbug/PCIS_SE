import base64
import csv
import io
import json
import re

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.api import LegacyAPIError, api_response
from apps.accounts.permissions import IsAdminRole

from datetime import date, datetime

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils.dateparse import parse_date, parse_datetime

from .models import ActivityLog, Category, Department, Floor, Item, Room, RoomType, SubCategory
from .serializers import (
    CategoryDescriptionSerializer,
    CategoryListSerializer,
    CategorySerializer,
    FloorListSerializer,
    FloorSerializer,
    DepartmentListSerializer,
    DepartmentSerializer,
    ItemReportSerializer,
    ItemSerializer,
    RoomNameListSerializer,
    RoomReportSerializer,
    RoomSerializer,
    RoomTypeListSerializer,
    RoomTypeSerializer,
    SubCategoryDescriptionSerializer,
    SubCategoryListSerializer,
    ActivityLogSerializer,
    SubCategorySerializer,
)

OBJECT_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")


def require_object_id(value):
    if not OBJECT_ID_PATTERN.fullmatch(value):
        raise LegacyAPIError(400, f"Invalid ObjectId: {value}")
    return value


FIELD_MAX_LENGTHS = {
    "departmentName": 200,
    "floorName": 200,
    "roomTypeName": 200,
    "categoryName": 200,
    "subCategoryName": 200,
    "subCategoryAbbreviation": 20,
    "roomName": 200,
    "roomNo": 50,
    "allottedTo": 200,
    "itemName": 200,
    "itemModelNumberOrMake": 200,
    "itemDescription": 2000,
    "itemRemark": 2000,
    "itemSerialNumber": 255,
}


def check_length(value, field_name):
    """Reject over-long input for the given field to prevent storage abuse."""
    if value is None:
        return
    max_len = FIELD_MAX_LENGTHS.get(field_name)
    if max_len is not None and len(value) > max_len:
        raise LegacyAPIError(400, f"{field_name} must be at most {max_len} characters")


def validate_item_cost(value):
    try:
        cost = float(value)
    except (TypeError, ValueError):
        raise LegacyAPIError(400, "Invalid item cost")
    if cost <= 0:
        raise LegacyAPIError(400, "Item cost must be greater than zero")
    return cost


def validate_item_acquired_date(value):
    parsed = parse_date(value)
    if parsed is None:
        parsed_datetime = parse_datetime(value)
        parsed = parsed_datetime.date() if parsed_datetime else None
    if parsed is None:
        raise LegacyAPIError(400, "Invalid item acquired date")
    if parsed > date.today():
        raise LegacyAPIError(400, "Item acquired date cannot be in the future")
    return parsed.isoformat()


ITEM_CREATE_COUNT_MAX = 100
CSV_IMPORT_MAX_BYTES = 5 * 1024 * 1024
CSV_IMPORT_MAX_ROWS = 5000
CSV_IMPORT_MAX_ITEMS = 5000
CSV_IMPORT_COLUMNS = (
    "department", "floor", "room", "room_type", "category", "subcategory",
    "item_name", "model_or_make", "source", "status", "cost", "acquired_date",
    "quantity", "description", "item_serial_number",
)
CSV_IMPORT_REQUIRED_COLUMNS = {
    "floor", "room", "item_name", "source", "status",
}
CSV_IMPORT_HEADER_ALIASES = {
    "department": "department",
    "department_name": "department",
    "floor": "floor",
    "floor_name": "floor",
    "room": "room",
    "room_name": "room",
    "room_type": "room_type",
    "roomtype": "room_type",
    "category": "category",
    "subcategory": "subcategory",
    "sub_category": "subcategory",
    "item_name": "item_name",
    "itemname": "item_name",
    "model_or_make": "model_or_make",
    "model": "model_or_make",
    "source": "source",
    "status": "status",
    "cost": "cost",
    "price": "cost",
    "acquired_date": "acquired_date",
    "quantity": "quantity",
    "description": "description",
    "id": "item_serial_number",
    "serial_number": "item_serial_number",
}
CSV_IMPORT_FALLBACK_DEPARTMENT = "Electronics and Computer Engineering"
CSV_IMPORT_FALLBACK_ROOM_TYPE = "Unspecified"


def validate_item_create_count(value):
    """Cap bulk item creation to avoid a resource-exhaustion DoS (M5)."""
    if value in (None, ""):
        return 1
    raw = str(value).strip()
    if not re.fullmatch(r"\d+", raw):
        raise LegacyAPIError(400, "Invalid item_create_count")
    count = int(raw)
    if count < 1:
        raise LegacyAPIError(400, "item_create_count must be at least 1")
    if count > ITEM_CREATE_COUNT_MAX:
        raise LegacyAPIError(
            400, f"item_create_count must not exceed {ITEM_CREATE_COUNT_MAX}"
        )
    return count


def _normalized(value):
    return value.strip().casefold()


def _csv_error(row_number, message):
    return {"row": row_number, "message": message}


def _normalized_csv_header(value):
    return re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")


def parse_item_import_csv(uploaded_file):
    """Read a small UTF-8 CSV and return its raw rows with validated headers."""
    if uploaded_file is None:
        raise LegacyAPIError(400, "A CSV file is required")
    if uploaded_file.size > CSV_IMPORT_MAX_BYTES:
        raise LegacyAPIError(400, "CSV file must not exceed 5 MB")
    if not uploaded_file.name.lower().endswith(".csv"):
        raise LegacyAPIError(400, "Please upload a CSV file")
    try:
        content = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise LegacyAPIError(400, "CSV file must be UTF-8 encoded")

    try:
        reader = csv.DictReader(io.StringIO(content))
        header_map = {}
        for header in reader.fieldnames or []:
            canonical_header = CSV_IMPORT_HEADER_ALIASES.get(_normalized_csv_header(header))
            if canonical_header:
                if canonical_header in header_map.values():
                    raise LegacyAPIError(400, f"CSV has duplicate column: {canonical_header}")
                header_map[header] = canonical_header
        headers = set(header_map.values())
        missing_columns = CSV_IMPORT_REQUIRED_COLUMNS - headers
        if missing_columns:
            raise LegacyAPIError(
                400,
                "CSV is missing required columns: " + ", ".join(sorted(missing_columns)),
            )
        missing_location_details = not {"department", "room_type"}.issubset(headers)
        rows = []
        for raw_row in reader:
            if not any(str(value or "").strip() for value in raw_row.values()):
                continue
            row = {
                canonical_header: raw_row.get(header) or ""
                for header, canonical_header in header_map.items()
            }
            row["_use_existing_location"] = missing_location_details
            rows.append(row)
    except csv.Error:
        raise LegacyAPIError(400, "CSV file could not be read")

    if not rows:
        raise LegacyAPIError(400, "CSV file does not contain any data rows")
    if len(rows) > CSV_IMPORT_MAX_ROWS:
        raise LegacyAPIError(400, f"CSV must not contain more than {CSV_IMPORT_MAX_ROWS} rows")
    return rows


def validate_item_import_rows(raw_rows):
    """Validate user-facing CSV values without writing to the database."""
    valid_rows = []
    errors = []
    source_lookup = {value.casefold(): value for value, _ in Item.Source.choices}
    status_lookup = {value.casefold(): value for value, _ in Item.Status.choices}

    for row_number, raw_row in enumerate(raw_rows, start=2):
        row = {column: (raw_row.get(column) or "").strip() for column in CSV_IMPORT_COLUMNS}
        row["_use_existing_location"] = raw_row.get("_use_existing_location", False)
        missing = [column for column in CSV_IMPORT_REQUIRED_COLUMNS if not row[column]]
        if missing:
            errors.append(_csv_error(row_number, "Missing required value: " + ", ".join(sorted(missing))))
            continue
        if row["subcategory"] and not row["category"]:
            errors.append(_csv_error(row_number, "A category is required when subcategory is provided"))
            continue

        field_lengths = {
            "department": "departmentName", "floor": "floorName", "room": "roomName",
            "room_type": "roomTypeName", "category": "categoryName",
            "subcategory": "subCategoryName", "item_name": "itemName",
            "model_or_make": "itemModelNumberOrMake", "description": "itemDescription",
            "item_serial_number": "itemSerialNumber",
        }
        too_long = next(
            (column for column, field in field_lengths.items()
             if len(row[column]) > FIELD_MAX_LENGTHS[field]),
            None,
        )
        if too_long:
            errors.append(_csv_error(row_number, f"{too_long} is too long"))
            continue

        source = source_lookup.get(row["source"].casefold())
        status = status_lookup.get(row["status"].casefold())
        if not source:
            errors.append(_csv_error(row_number, "Source must be Purchase or Donation"))
            continue
        if not status:
            errors.append(_csv_error(row_number, "Status must be Working, Repairable, or Not working"))
            continue
        try:
            quantity = validate_item_create_count(row["quantity"] or 1)
        except LegacyAPIError:
            errors.append(_csv_error(row_number, "Quantity must be a whole number from 1 to 100"))
            continue
        try:
            cost = validate_item_cost(row["cost"]) if row["cost"] else None
            acquired_date = validate_item_acquired_date(row["acquired_date"]) if row["acquired_date"] else None
        except LegacyAPIError as exc:
            errors.append(_csv_error(row_number, str(exc.detail)))
            continue

        row.update({"source": source, "status": status, "quantity": quantity, "cost": cost, "acquired_date": acquired_date})
        if row["_use_existing_location"]:
            row["department"] = CSV_IMPORT_FALLBACK_DEPARTMENT
            row["room_type"] = CSV_IMPORT_FALLBACK_ROOM_TYPE
        valid_rows.append(row)

    total_items = sum(row["quantity"] for row in valid_rows)
    if total_items > CSV_IMPORT_MAX_ITEMS:
        errors.append(_csv_error(0, f"CSV cannot create more than {CSV_IMPORT_MAX_ITEMS} items"))
    return valid_rows, errors, total_items


def generate_item_serial(sub_category_id):
    """Allocate the next serial number for an item subcategory."""
    year = datetime.now().strftime("%Y")
    if not sub_category_id:
        return f"{year}XXX001"
    sub = SubCategory.objects.get(pk=sub_category_id)
    abbreviation = sub.subCategoryAbbreviation or "XXX"
    sub.lastItemSerialNumber += 1
    sub.save(update_fields=["lastItemSerialNumber", "updated_at"])
    return f"{year}{abbreviation}{str(sub.lastItemSerialNumber).zfill(3)}"


def get_or_create_import_references(row, user):
    """Resolve the named hierarchy in a CSV row, creating only missing references."""
    floor = room = None
    if row["_use_existing_location"]:
        room = Room.objects.filter(
            roomNameNormalized=_normalized(row["room"]),
            floor__floorNameNormalized=_normalized(row["floor"]),
            floor__isActive=True,
            isActive=True,
        ).select_related("floor").first()
        if room:
            floor = room.floor
    if floor is None:
        department, _ = Department.objects.get_or_create(
            departmentNameNormalized=_normalized(row["department"]),
            isActive=True,
            defaults={"departmentName": row["department"], "createdBy": user},
        )
        floor, _ = Floor.objects.get_or_create(
            floorNameNormalized=_normalized(row["floor"]), department=department, isActive=True,
            defaults={"floorName": row["floor"], "createdBy": user},
        )
        room_type, _ = RoomType.objects.get_or_create(
            roomTypeNameNormalized=_normalized(row["room_type"]), department=department, isActive=True,
            defaults={"roomTypeName": row["room_type"], "createdBy": user},
        )
        room, _ = Room.objects.get_or_create(
            roomNameNormalized=_normalized(row["room"]), floor=floor, roomType=room_type, isActive=True,
            defaults={"roomName": row["room"], "createdBy": user},
        )
    category = None
    sub_category = None
    if row["category"]:
        category, _ = Category.objects.get_or_create(
            categoryNameNormalized=_normalized(row["category"]), isActive=True,
            defaults={"categoryName": row["category"], "createdBy": user},
        )
    if row["subcategory"]:
        abbreviation = "".join(char for char in row["subcategory"].upper() if char.isalnum())[:20] or "CSV"
        sub_category, _ = SubCategory.objects.get_or_create(
            subCategoryNameNormalized=_normalized(row["subcategory"]), category=category, isActive=True,
            defaults={
                "subCategoryName": row["subcategory"],
                "subCategoryAbbreviation": abbreviation,
                "subCategoryAbbreviationNormalized": abbreviation.casefold(),
                "createdBy": user,
            },
        )
    return floor, room, category, sub_category


def log_activity(
    request,
    action,
    entity_type,
    entity=None,
    entity_id=None,
    entity_name=None,
    description=None,
    changes=None,
):
    user = getattr(request, "user", None)
    if user is not None and not user.is_authenticated:
        user = None
    ActivityLog.objects.create(
        action=action,
        entityType=entity_type,
        entityId=entity_id or (entity.pk if entity else None),
        entityName=entity_name,
        description=description,
        performedByName=user.username if user else None,
        performedByRole=user.role if user else None,
        performedBy=user,
        changes=changes,
    )


class DepartmentListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def get(self, request):
        departments = Department.objects.filter(isActive=True).order_by("departmentName")
        return api_response(200, DepartmentListSerializer(departments, many=True).data, "All departments fetched successfully")

    def post(self, request):
        name = request.data.get("departmentName")
        if not name or not name.strip():
            raise LegacyAPIError(400, "Department name is required.")
        check_length(name, "departmentName")
        normalized = name.strip().lower()
        if Department.objects.filter(isActive=True, departmentNameNormalized=normalized).exists():
            raise LegacyAPIError(409, "Department already exists")
        department = Department.objects.create(departmentName=name.strip(), departmentNameNormalized=normalized, createdBy=request.user)
        log_activity(request, "Department added", ActivityLog.EntityType.DEPARTMENT, entity=department, entity_name=department.departmentName)
        return api_response(201, DepartmentSerializer(department).data, "Department added successfully")


class DepartmentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, department_id):
        department_id = require_object_id(department_id.strip())
        name = request.data.get("departmentName")
        if not name or not name.strip():
            raise LegacyAPIError(400, "Department name is required.")
        check_length(name, "departmentName")
        normalized = name.strip().lower()
        try:
            department = Department.objects.get(pk=department_id)
        except Department.DoesNotExist:
            raise LegacyAPIError(404, "Department not found")
        if Department.objects.filter(isActive=True, departmentNameNormalized=normalized).exclude(pk=department_id).exists():
            raise LegacyAPIError(409, "Department name already in use")
        department.departmentName = name.strip()
        department.departmentNameNormalized = normalized
        department.save(update_fields=["departmentName", "departmentNameNormalized", "updated_at"])
        log_activity(request, "Department updated", ActivityLog.EntityType.DEPARTMENT, entity=department, entity_name=department.departmentName)
        return api_response(200, DepartmentSerializer(department).data, "Department updated successfully")

    def delete(self, request, department_id):
        department_id = require_object_id(department_id.strip())
        try:
            department = Department.objects.get(pk=department_id)
        except Department.DoesNotExist:
            raise LegacyAPIError(404, "Department not found")
        if not department.isActive:
            raise LegacyAPIError(400, "Department has already been removed")
        department.isActive = False
        department.save(update_fields=["isActive", "updated_at"])
        log_activity(request, "Department deleted", ActivityLog.EntityType.DEPARTMENT, entity=department, entity_name=department.departmentName)
        return api_response(200, {}, "Department deleted successfully")


class FloorListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def get(self, request):
        department_id = _optional_department_id(request.query_params.get("department_id"))
        floors = Floor.objects.filter(isActive=True)
        if department_id:
            floors = floors.filter(department_id=department_id)
        if not floors.exists():
            raise LegacyAPIError(404, "Floors not found")
        return api_response(
            200,
            FloorListSerializer(floors, many=True).data,
            "All floors fetched successfully",
        )

    def post(self, request):
        floor_name = request.data.get("floorName")
        department_id = _optional_department_id(request.data.get("departmentId"))
        check_length(floor_name, "floorName")
        normalized = floor_name.lower()
        if Floor.objects.filter(isActive=True, floorNameNormalized=normalized, department_id=department_id).exists():
            raise LegacyAPIError(409, "Floor already exists")
        floor = Floor.objects.create(
            floorName=floor_name,
            createdBy=request.user,
            floorNameNormalized=normalized,
            department_id=department_id,
        )
        log_activity(
            request,
            "Floor added",
            ActivityLog.EntityType.FLOOR,
            entity=floor,
            entity_name=floor.floorName,
        )
        return api_response(201, FloorSerializer(floor).data, "Floor added successfully")


class FloorDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, floor_id):
        floor_id = require_object_id(floor_id.strip())
        floor_name = request.data.get("floorName")
        department_id = _optional_department_id(request.data.get("departmentId")) if "departmentId" in request.data else None
        check_length(floor_name, "floorName")
        normalized = floor_name.lower()
        try:
            floor = Floor.objects.get(pk=floor_id)
        except Floor.DoesNotExist:
            raise LegacyAPIError(404, "Floor with the given id not found.")
        if Floor.objects.filter(isActive=True, floorNameNormalized=normalized, department_id=department_id if "departmentId" in request.data else floor.department_id).exclude(
            pk=floor_id
        ).exists():
            raise LegacyAPIError(409, "Floor name already in use.")
        floor.floorName = floor_name
        floor.floorNameNormalized = normalized
        if "departmentId" in request.data:
            floor.department_id = department_id
        floor.save(update_fields=["floorName", "floorNameNormalized", "department", "updated_at"])
        log_activity(
            request,
            "Floor updated",
            ActivityLog.EntityType.FLOOR,
            entity=floor,
            entity_name=floor.floorName,
        )
        return api_response(200, FloorSerializer(floor).data, "Floor updated successfully.")

    def delete(self, request, floor_id):
        floor_id = require_object_id(floor_id.strip())
        try:
            floor = Floor.objects.get(pk=floor_id)
        except Floor.DoesNotExist:
            raise LegacyAPIError(404, "Floor not found")
        if not floor.isActive:
            raise LegacyAPIError(400, "Floor has been removed already")
        floor.isActive = False
        floor.save(update_fields=["isActive", "updated_at"])
        log_activity(
            request,
            "Floor deleted",
            ActivityLog.EntityType.FLOOR,
            entity=floor,
            entity_name=floor.floorName,
        )
        return api_response(200, {}, "Floor Deleted Successfully")


class RoomTypeListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def get(self, request):
        department_id = _optional_department_id(request.query_params.get("department_id"))
        types = RoomType.objects.filter(isActive=True)
        if department_id:
            types = types.filter(department_id=department_id)
        if not types.exists():
            raise LegacyAPIError(404, "Room types not found")
        return api_response(
            200,
            RoomTypeListSerializer(types, many=True).data,
            "All room types fetched successfully",
        )

    def post(self, request):
        room_type_name = request.data.get("roomTypeName")
        department_id = _optional_department_id(request.data.get("departmentId"))
        if not room_type_name or not room_type_name.strip():
            raise LegacyAPIError(400, "Room type name is required.")
        check_length(room_type_name, "roomTypeName")
        normalized = room_type_name.strip().lower()
        if RoomType.objects.filter(isActive=True, roomTypeNameNormalized=normalized, department_id=department_id).exists():
            raise LegacyAPIError(409, "Room type already exists")
        room_type = RoomType.objects.create(
            roomTypeName=room_type_name.strip(),
            createdBy=request.user,
            roomTypeNameNormalized=normalized,
            department_id=department_id,
        )
        log_activity(
            request,
            "Room type registered",
            ActivityLog.EntityType.ROOMTYPE,
            entity=room_type,
            entity_name=room_type.roomTypeName,
        )
        return api_response(
            201, RoomTypeSerializer(room_type).data, "Room type registered successfully"
        )


class RoomTypeDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, room_type_id):
        room_type_id = require_object_id(room_type_id.strip())
        room_type_name = request.data.get("roomTypeName")
        department_id = _optional_department_id(request.data.get("departmentId")) if "departmentId" in request.data else None
        if not room_type_name or not room_type_name.strip():
            raise LegacyAPIError(400, "Room type name is required.")
        check_length(room_type_name, "roomTypeName")
        normalized = room_type_name.strip().lower()
        try:
            room_type = RoomType.objects.get(pk=room_type_id)
        except RoomType.DoesNotExist:
            raise LegacyAPIError(404, "Room tupe with given id not found.")
        if RoomType.objects.filter(isActive=True, roomTypeNameNormalized=normalized, department_id=department_id if "departmentId" in request.data else room_type.department_id).exclude(
            pk=room_type_id
        ).exists():
            raise LegacyAPIError(409, "Room type name already in use")
        room_type.roomTypeName = room_type_name.strip()
        room_type.roomTypeNameNormalized = normalized
        if "departmentId" in request.data:
            room_type.department_id = department_id
        room_type.save(update_fields=["roomTypeName", "roomTypeNameNormalized", "department", "updated_at"])
        log_activity(
            request,
            "Room type updated",
            ActivityLog.EntityType.ROOMTYPE,
            entity=room_type,
            entity_name=room_type.roomTypeName,
        )
        return api_response(
            200, RoomTypeSerializer(room_type).data, "Room type name updated successfully"
        )

    def delete(self, request, room_type_id):
        room_type_id = require_object_id(room_type_id.strip())
        try:
            room_type = RoomType.objects.get(pk=room_type_id)
        except RoomType.DoesNotExist:
            raise LegacyAPIError(404, "Room type not found")
        if not room_type.isActive:
            raise LegacyAPIError(400, "Room type has already been removed.")
        room_type.isActive = False
        room_type.save(update_fields=["isActive", "updated_at"])
        log_activity(
            request,
            "Room type deleted",
            ActivityLog.EntityType.ROOMTYPE,
            entity=room_type,
            entity_name=room_type.roomTypeName,
        )
        return api_response(200, {}, "Room type deleted successfully")


PAGINATION_LIMIT = 6
ITEM_QUERY_PAGINATION_LIMIT = 15


def _optional_object_id(value, field_name):
    """Return an optional object id, rejecting malformed supplied values."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return require_object_id(value)
    except LegacyAPIError:
        raise LegacyAPIError(400, f"Invalid {field_name}")


def _optional_department_id(value):
    """Validate an optional department and ensure it is an active reference."""
    department_id = _optional_object_id(value, "department id")
    if department_id and not Department.objects.filter(pk=department_id, isActive=True).exists():
        raise LegacyAPIError(404, "Department not found")
    return department_id


def _decode_item_cursor(cursor):
    """Decode an opaque cursor for the `-updated_at, -id` item ordering."""
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        updated_at = parse_datetime(payload["updated_at"])
        item_id = require_object_id(payload["id"])
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError, LegacyAPIError):
        raise LegacyAPIError(400, "Invalid search cursor")
    if updated_at is None:
        raise LegacyAPIError(400, "Invalid search cursor")
    return updated_at, item_id


def _encode_item_cursor(item):
    payload = json.dumps(
        {"updated_at": item.updated_at.isoformat(), "id": item.pk},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


class CategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def get(self, request):
        categories = Category.objects.filter(isActive=True)
        return api_response(
            200,
            CategoryListSerializer(categories, many=True).data,
            "All  active categories fetched successfully",
        )

    def post(self, request):
        category_name = request.data.get("categoryName")
        if not category_name or not category_name.strip():
            raise LegacyAPIError(400, "Bad request.Category name is required.")
        check_length(category_name, "categoryName")
        normalized = category_name.strip().lower()
        if Category.objects.filter(isActive=True, categoryNameNormalized=normalized).exists():
            raise LegacyAPIError(409, "Category already exists")
        category = Category.objects.create(
            categoryName=category_name.strip(),
            createdBy=request.user,
            categoryNameNormalized=normalized,
        )
        log_activity(
            request,
            "Category added",
            ActivityLog.EntityType.CATEGORY,
            entity=category,
            entity_name=category.categoryName,
        )
        return api_response(201, CategorySerializer(category).data, "Category added successfully")


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, category_id):
        category_id = require_object_id(category_id.strip())
        category_name = request.data.get("categoryName")
        if not category_name or not category_name.strip():
            raise LegacyAPIError(400, "Bad request.All the fields are empty.")
        check_length(category_name, "categoryName")
        normalized = category_name.strip().lower()
        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            raise LegacyAPIError(404, "Category with given id not found.")
        if Category.objects.filter(isActive=True, categoryNameNormalized=normalized).exclude(
            pk=category_id
        ).exists():
            raise LegacyAPIError(409, "Category name is already taken")
        category.categoryName = category_name.strip()
        category.categoryNameNormalized = normalized
        category.save(update_fields=["categoryName", "categoryNameNormalized", "updated_at"])
        log_activity(
            request,
            "Category updated",
            ActivityLog.EntityType.CATEGORY,
            entity=category,
            entity_name=category.categoryName,
        )
        return api_response(
            200, CategorySerializer(category).data, "Category details updated successfully."
        )

    def delete(self, request, category_id):
        category_id = require_object_id(category_id.strip())
        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            raise LegacyAPIError(404, "Category not found")
        if not category.isActive:
            raise LegacyAPIError(400, "Category has already been removed.")
        category.isActive = False
        category.save(update_fields=["isActive", "updated_at"])
        log_activity(
            request,
            "Category deleted",
            ActivityLog.EntityType.CATEGORY,
            entity=category,
            entity_name=category.categoryName,
        )
        return api_response(200, {}, "Category Deleted Successfully")


class CategoryDescriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, page):
        try:
            page_number = int(page) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        total = Category.objects.filter(isActive=True).count()
        if total == 0:
            return api_response(
                200,
                {"totalCategories": 0, "categories": []},
                "All category data fetched successfully.",
            )
        start = (page_number - 1) * PAGINATION_LIMIT
        end = page_number * PAGINATION_LIMIT
        categories = Category.objects.filter(isActive=True).select_related("createdBy")[
            start:end
        ]
        return api_response(
            200,
            {
                "totalCategories": total,
                "categories": CategoryDescriptionSerializer(categories, many=True).data,
            },
            "All category data fetched successfully.",
        )


class SubCategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def get(self, request, category_id):
        category_id = require_object_id(category_id.strip())
        subcategories = SubCategory.objects.filter(isActive=True, category_id=category_id)
        return api_response(
            200,
            SubCategoryListSerializer(subcategories, many=True).data,
            "All SubCategories fetched successfully",
        )

    def post(self, request, category_id):
        category_id = require_object_id(category_id.strip())
        sub_name = request.data.get("subCategoryName")
        sub_abbr = request.data.get("subCategoryAbbreviation")
        if not (sub_name and sub_abbr):
            raise LegacyAPIError(400, "Bad request.Fill all the fields.")
        check_length(sub_name, "subCategoryName")
        check_length(sub_abbr, "subCategoryAbbreviation")
        normalized_name = sub_name.strip().lower()
        normalized_abbr = sub_abbr.strip().lower()
        if not Category.objects.filter(pk=category_id).exists():
            raise LegacyAPIError(404, "Category not found")
        if SubCategory.objects.filter(
            isActive=True,
        ).filter(
            subCategoryNameNormalized=normalized_name,
        ).exists():
            raise LegacyAPIError(409, "SubCategory already exists")
        if SubCategory.objects.filter(
            isActive=True,
        ).filter(
            subCategoryAbbreviationNormalized=normalized_abbr,
        ).exists():
            raise LegacyAPIError(409, "SubCategory already exists")
        subcategory = SubCategory.objects.create(
            subCategoryName=sub_name.strip(),
            subCategoryAbbreviation=sub_abbr.strip(),
            subCategoryNameNormalized=normalized_name,
            subCategoryAbbreviationNormalized=normalized_abbr,
            createdBy=request.user,
            category_id=category_id,
        )
        log_activity(
            request,
            "SubCategory added",
            ActivityLog.EntityType.SUBCATEGORY,
            entity=subcategory,
            entity_name=subcategory.subCategoryName,
        )
        return api_response(
            201, SubCategorySerializer(subcategory).data, "SubCategory added successfully."
        )


class SubCategoryDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, category_id, sub_category_id):
        category_id = require_object_id(category_id.strip())
        sub_category_id = require_object_id(sub_category_id.strip())
        if not Category.objects.filter(pk=category_id).exists():
            raise LegacyAPIError(404, "Category not found")
        try:
            subcategory = SubCategory.objects.get(pk=sub_category_id)
        except SubCategory.DoesNotExist:
            raise LegacyAPIError(404, "Sub Category not found")
        if not subcategory.isActive:
            raise LegacyAPIError(400, "Sub category has already been removed.")
        subcategory.isActive = False
        subcategory.save(update_fields=["isActive", "updated_at"])
        log_activity(
            request,
            "SubCategory deleted",
            ActivityLog.EntityType.SUBCATEGORY,
            entity=subcategory,
            entity_name=subcategory.subCategoryName,
        )
        return api_response(200, {}, "Sub category deleted successfully")


class SubCategoryDescriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, category_id):
        category_id = require_object_id(category_id.strip())
        total = SubCategory.objects.filter(isActive=True, category_id=category_id).count()
        if total == 0:
            return api_response(
                200,
                {"totalSubCategories": 0, "subCategories": []},
                "All  sub category data fetched successfully.",
            )
        subcategories = SubCategory.objects.filter(
            isActive=True, category_id=category_id
        ).select_related("createdBy")
        return api_response(
            200,
            {
                "totalSubCategories": total,
                "subCategories": SubCategoryDescriptionSerializer(subcategories, many=True).data,
            },
            "All  sub category data fetched successfully.",
        )


class RoomCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        room_name = request.data.get("room_name")
        room_no = request.data.get("room_no")
        room_floor_id = request.data.get("room_floor_id")
        room_type_id = request.data.get("room_type_id")
        allotted_to = request.data.get("allotted_to")
        if not (room_name and room_floor_id and room_type_id):
            raise LegacyAPIError(400, "Bad request.Request body is insufficient.")
        check_length(room_name, "roomName")
        check_length(room_no, "roomNo")
        check_length(allotted_to, "allottedTo")
        room_floor_id = require_object_id(room_floor_id.strip())
        room_type_id = require_object_id(room_type_id.strip())
        try:
            floor = Floor.objects.get(pk=room_floor_id, isActive=True)
        except Floor.DoesNotExist:
            raise LegacyAPIError(404, "Floor not found")
        try:
            room_type = RoomType.objects.get(pk=room_type_id, isActive=True)
        except RoomType.DoesNotExist:
            raise LegacyAPIError(404, "Room type not found")
        if floor.department_id != room_type.department_id:
            raise LegacyAPIError(400, "Floor and room type must belong to the same department")
        query = {
            "roomName": room_name.strip(),
            "floor_id": room_floor_id,
            "roomType_id": room_type_id,
            "createdBy": request.user,
            "roomNameNormalized": room_name.strip().lower(),
        }
        if room_no:
            query["roomNo"] = room_no.strip()
        if allotted_to:
            query["allottedTo"] = allotted_to.strip()
        if Room.objects.filter(**{
            k: v for k, v in query.items()
            if k in ("roomName", "floor_id", "roomType_id")
        }).exists():
            raise LegacyAPIError(409, "Room already exists")
        room = Room.objects.create(**query)
        log_activity(
            request,
            "Room added",
            ActivityLog.EntityType.ROOM,
            entity=room,
            entity_name=room.roomName,
        )
        return api_response(201, RoomSerializer(room).data, "Room added successfully.")


class RoomView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]

    def get(self, request, identifier):
        identifier = identifier.strip()
        if OBJECT_ID_PATTERN.fullmatch(identifier):
            try:
                room = Room.objects.select_related(
                    "floor", "roomType", "createdBy"
                ).get(pk=identifier, isActive=True)
            except Room.DoesNotExist:
                raise LegacyAPIError(404, "Room not found")
            return api_response(
                200, RoomReportSerializer(room).data, "Room fetched successfully"
            )
        try:
            page_number = int(identifier) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        start = (page_number - 1) * PAGINATION_LIMIT
        end = page_number * PAGINATION_LIMIT
        total = Room.objects.filter(isActive=True).count()
        if total == 0:
            return api_response(
                200,
                {"totalRooms": 0, "rooms": []},
                "All rooms data fetched successfully",
                payload_status_code=201,
            )
        rooms = Room.objects.filter(isActive=True).select_related(
            "floor", "roomType", "createdBy"
        ).order_by("-updated_at")[start:end]
        return api_response(
            200,
            {"totalRooms": total, "rooms": RoomReportSerializer(rooms, many=True).data},
            "All rooms data fetched successfully",
            payload_status_code=201,
        )

    def patch(self, request, identifier):
        room_id = require_object_id(identifier.strip())
        room_name = request.data.get("room_name")
        room_no = request.data.get("room_no")
        room_floor_id = request.data.get("room_floor_id")
        room_type_id = request.data.get("room_type_id")
        allotted_to = request.data.get("allotted_to")
        if not (room_name or room_no or room_floor_id or room_type_id or allotted_to is not None):
            raise LegacyAPIError(400, "Please provide at least one of the fields to update")
        check_length(room_name, "roomName")
        check_length(room_no, "roomNo")
        check_length(allotted_to, "allottedTo")
        try:
            room = Room.objects.get(pk=room_id)
        except Room.DoesNotExist:
            raise LegacyAPIError(404, "Room with the given id not found.")
        if room_name:
            normalized = room_name.strip().lower()
            if Room.objects.filter(isActive=True, roomNameNormalized=normalized).exclude(
                pk=room_id
            ).exists():
                raise LegacyAPIError(409, "Room name already taken")
            room.roomName = room_name.strip()
            room.roomNameNormalized = normalized
        if room_no is not None:
            room.roomNo = room_no.strip() if room_no else ""
        if room_floor_id:
            room_floor_id = require_object_id(room_floor_id.strip())
            if not Floor.objects.filter(pk=room_floor_id).exists():
                raise LegacyAPIError(404, "Floor with the provided id not found.")
            room.floor_id = room_floor_id
        if room_type_id:
            room_type_id = require_object_id(room_type_id.strip())
            if not RoomType.objects.filter(pk=room_type_id).exists():
                raise LegacyAPIError(404, "Room type with the provided id not found.")
            room.roomType_id = room_type_id
        if room.floor_id and room.roomType_id:
            if room.floor.department_id != room.roomType.department_id:
                raise LegacyAPIError(400, "Floor and room type must belong to the same department")
        if allotted_to is not None:
            room.allottedTo = allotted_to.strip() if allotted_to else ""
        room.save()
        log_activity(
            request,
            "Room updated",
            ActivityLog.EntityType.ROOM,
            entity=room,
            entity_name=room.roomName,
        )
        return api_response(200, RoomSerializer(room).data, "Room deatils updated successfully.")

    def delete(self, request, identifier):
        room_id = require_object_id(identifier.strip())
        try:
            room = Room.objects.get(pk=room_id)
        except Room.DoesNotExist:
            raise LegacyAPIError(404, "Room not found")
        room.isActive = False
        room.save(update_fields=["isActive", "updated_at"])
        log_activity(
            request,
            "Room deleted",
            ActivityLog.EntityType.ROOM,
            entity=room,
            entity_name=room.roomName,
        )
        return api_response(200, {}, "Room deleted successfully")


class RoomFloorFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, floor_id, page=None):
        department_id = _optional_department_id(request.query_params.get("department_id"))
        if page is not None:
            floor_id = floor_id.strip()
            filter_kwargs = {"isActive": True}
            if department_id:
                filter_kwargs["floor__department_id"] = department_id
            if floor_id and floor_id != "0":
                floor_id = require_object_id(floor_id)
                filter_kwargs["floor_id"] = floor_id
            try:
                page_number = int(page) or 1
            except ValueError:
                page_number = 1
            page_number = max(page_number, 1)
            start = (page_number - 1) * PAGINATION_LIMIT
            end = page_number * PAGINATION_LIMIT
            total = Room.objects.filter(**filter_kwargs).count()
            if total == 0:
                return api_response(
                    200,
                    {"totalRooms": 0, "rooms": []},
                    f"Details of rooms belonging to floor with id {floor_id} fetched successfully",
                )
            rooms = Room.objects.filter(**filter_kwargs).select_related(
                "floor", "roomType", "createdBy"
            ).order_by("-updated_at")[start:end]
            return api_response(
                200,
                {"totalRooms": total, "rooms": RoomReportSerializer(rooms, many=True).data},
                f"Details of rooms belonging to floor with id {floor_id} fetched successfully",
            )
        else:
            floor_id = floor_id.strip()
            filter_kwargs = {"isActive": True}
            if department_id:
                filter_kwargs["floor__department_id"] = department_id
            if floor_id and floor_id != "0":
                floor_id = require_object_id(floor_id)
                filter_kwargs["floor_id"] = floor_id
            total = Room.objects.filter(**filter_kwargs).count()
            if total == 0:
                return api_response(200, [], "Zero valid rooms.")
            rooms = Room.objects.filter(**filter_kwargs).select_related(
                "floor", "floor__department"
            ).order_by("roomName")
            return api_response(
                200,
                RoomNameListSerializer(rooms, many=True).data,
                f"Rooms of floor with id '{floor_id}' fetched successfully."
                if floor_id and floor_id != "0"
                else "All rooms fetched successfully.",
            )


class RoomSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_string, page):
        if not room_string:
            raise LegacyAPIError(400, "Room String is not available.")
        try:
            page_number = int(page) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        start = (page_number - 1) * PAGINATION_LIMIT
        end = page_number * PAGINATION_LIMIT
        filter_q = Q(isActive=True) & (
            Q(roomName__icontains=room_string) | Q(allottedTo__icontains=room_string)
        )
        department_id = _optional_department_id(request.query_params.get("department_id"))
        if department_id:
            filter_q &= Q(floor__department_id=department_id)
        total = Room.objects.filter(filter_q).count()
        if total == 0:
            return api_response(
                200,
                {"totalRooms": 0, "rooms": []},
                f"Details of rooms matching '{room_string}' fetched successfully",
            )
        rooms = Room.objects.filter(filter_q).select_related(
            "floor", "roomType", "createdBy"
        ).order_by("-updated_at")[start:end]
        return api_response(
            200,
            {"totalRooms": total, "rooms": RoomReportSerializer(rooms, many=True).data},
            f"Details of rooms matching '{room_string}' fetched successfully",
        )


ITEM_SOURCE_DATA = [
    {"sourceName": "Purchase", "sourceId": "1357"},
    {"sourceName": "Donation", "sourceId": "2468"},
]

ITEM_STATUS_DATA = [
    {"statusName": "Working", "statusId": "1234"},
    {"statusName": "Repairable", "statusId": "3456"},
    {"statusName": "Not working", "statusId": "5678"},
]


class ItemCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        item_name = request.data.get("itemName")
        item_category_id = request.data.get("itemCategory")
        item_sub_category_id = request.data.get("itemSubCategory")
        item_floor_id = request.data.get("itemFloor")
        item_room_id = request.data.get("itemRoom")
        item_source = request.data.get("itemSource")
        item_cost = request.data.get("itemCost")
        item_status = request.data.get("itemStatus")
        item_acquired_date = request.data.get("itemAcquiredDate")
        item_create_count = request.data.get("item_create_count")

        required = [
            ("itemName", item_name), ("itemFloor", item_floor_id),
            ("itemRoom", item_room_id), ("itemSource", item_source),
            ("itemStatus", item_status),
        ]
        for field_name, val in required:
            if not val:
                raise LegacyAPIError(400, f"Invalid {field_name}")

        item_cost = validate_item_cost(item_cost) if item_cost else None
        if item_acquired_date:
            item_acquired_date = validate_item_acquired_date(item_acquired_date)
        check_length(item_name, "itemName")
        check_length(request.data.get("itemModelNumberOrMake"), "itemModelNumberOrMake")
        check_length(request.data.get("itemDescription"), "itemDescription")
        check_length(request.data.get("itemSerialNumber"), "itemSerialNumber")

        item_floor_id = require_object_id(item_floor_id.strip())
        item_room_id = require_object_id(item_room_id.strip())

        try:
            floor = Floor.objects.get(pk=item_floor_id, isActive=True)
        except Floor.DoesNotExist:
            raise LegacyAPIError(404, "Invalid floor")
        try:
            room = Room.objects.get(pk=item_room_id, isActive=True)
        except Room.DoesNotExist:
            raise LegacyAPIError(404, "Invalid room")
        if room.floor_id != floor.pk:
            raise LegacyAPIError(400, "The room does not belong to the selected floor")
        if item_source not in dict(Item.Source.choices):
            raise LegacyAPIError(404, "Invalid source")
        if item_status not in dict(Item.Status.choices):
            raise LegacyAPIError(404, "Invalid status")

        item_category = None
        item_sub_category = None
        if item_category_id:
            item_category_id = require_object_id(item_category_id.strip())
            if not Category.objects.filter(pk=item_category_id).exists():
                raise LegacyAPIError(404, "Invalid category")
            item_category = item_category_id
        if item_sub_category_id:
            item_sub_category_id = require_object_id(item_sub_category_id.strip())
            if not SubCategory.objects.filter(pk=item_sub_category_id).exists():
                raise LegacyAPIError(404, "Invalid subcategory")
            item_sub_category = item_sub_category_id

        count = validate_item_create_count(item_create_count)
        items = []
        for _ in range(count):
            serial = self._generate_serial(item_sub_category)
            items.append(Item(
                itemName=item_name.strip(),
                itemCategory_id=item_category,
                itemSubCategory_id=item_sub_category,
                itemModelNumberOrMake=request.data.get("itemModelNumberOrMake"),
                itemAcquiredDate=item_acquired_date,
                itemCost=item_cost,
                itemFloor_id=item_floor_id,
                itemRoom_id=item_room_id,
                itemStatus=item_status,
                itemSource=item_source,
                itemDescription=request.data.get("itemDescription"),
                itemSerialNumber=serial,
                createdBy=request.user,
            ))
        created = Item.objects.bulk_create(items)
        log_activity(
            request,
            "Items created",
            ActivityLog.EntityType.ITEM,
            entity_id=item_category_id,
            entity_name=item_name.strip(),
            description=f"{count} item(s) created",
        )
        return api_response(
            201,
            ItemSerializer(created, many=True).data,
            "Items created successfully",
        )

    def _generate_serial(self, sub_category_id):
        return generate_item_serial(sub_category_id)


class ItemCSVImportPreviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        raw_rows = parse_item_import_csv(request.FILES.get("file"))
        valid_rows, errors, total_items = validate_item_import_rows(raw_rows)
        return api_response(
            200,
            {
                "fileName": request.FILES["file"].name,
                "totalRows": len(raw_rows),
                "validRows": len(valid_rows),
                "totalItems": total_items,
                "errors": errors[:50],
            },
            "CSV is ready to import" if not errors else "CSV has rows that need attention",
        )


class ItemCSVImportCommitView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        raw_rows = parse_item_import_csv(uploaded_file)
        valid_rows, errors, total_items = validate_item_import_rows(raw_rows)
        if errors:
            raise LegacyAPIError(400, "CSV contains invalid rows", errors=errors[:50])

        with transaction.atomic():
            created_items = []
            for row in valid_rows:
                floor, room, category, sub_category = get_or_create_import_references(row, request.user)
                for _ in range(row["quantity"]):
                    created_items.append(
                        Item(
                            itemName=row["item_name"],
                            itemCategory=category,
                            itemSubCategory=sub_category,
                            itemModelNumberOrMake=row["model_or_make"] or None,
                            itemAcquiredDate=row["acquired_date"],
                            itemCost=row["cost"],
                            itemFloor=floor,
                            itemRoom=room,
                            itemStatus=row["status"],
                            itemSource=row["source"],
                            itemDescription=row["description"] or None,
                            itemSerialNumber=(
                                row["item_serial_number"]
                                or generate_item_serial(sub_category.pk if sub_category else None)
                            ),
                            createdBy=request.user,
                        )
                    )
            Item.objects.bulk_create(created_items)
            log_activity(
                request,
                "Items imported from CSV",
                ActivityLog.EntityType.ITEM,
                entity_name=uploaded_file.name,
                description=f"Imported {total_items} item(s) from {len(valid_rows)} CSV row(s)",
                changes={"fileName": uploaded_file.name, "rows": len(valid_rows), "items": total_items},
            )
        return api_response(
            201,
            {"fileName": uploaded_file.name, "importedRows": len(valid_rows), "importedItems": total_items},
            "CSV imported successfully",
        )


class ItemSourceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return api_response(200, ITEM_SOURCE_DATA, "Item sources fetched successfully")


class ItemStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return api_response(200, ITEM_STATUS_DATA, "Item statuses fetched successfully")


class ItemSingleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        item_id = require_object_id(item_id.strip())
        try:
            item = Item.objects.select_related(
                "itemFloor", "itemRoom", "createdBy"
            ).get(pk=item_id, isActive=True)
        except Item.DoesNotExist:
            raise LegacyAPIError(404, "Item not found")
        return api_response(200, ItemReportSerializer(item).data, "Item fetched successfully")


class ItemAllView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, page):
        try:
            page_number = int(page) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        start = (page_number - 1) * PAGINATION_LIMIT
        end = page_number * PAGINATION_LIMIT
        total = Item.objects.filter(isActive=True).count()
        items = Item.objects.filter(isActive=True).select_related(
            "itemCategory", "itemSubCategory", "itemFloor", "itemRoom", "createdBy"
        ).order_by("-updated_at")[start:end]
        return api_response(
            200,
            {"totalItems": total, "items": ItemReportSerializer(items, many=True).data},
            "All items fetched successfully",
        )


class ItemSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_string, page):
        try:
            page_number = int(page) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        start = (page_number - 1) * PAGINATION_LIMIT
        end = page_number * PAGINATION_LIMIT
        q = Q(isActive=True) & (
            Q(itemName__icontains=item_string) | Q(itemSerialNumber__icontains=item_string)
        )
        department_id = _optional_department_id(request.query_params.get("department_id"))
        if department_id:
            q &= Q(itemFloor__department_id=department_id)
        total = Item.objects.filter(q).count()
        items = Item.objects.filter(q).select_related(
            "itemCategory", "itemSubCategory", "itemFloor", "itemRoom", "createdBy"
        ).order_by("-updated_at")[start:end]
        return api_response(
            200,
            {"totalItems": total, "items": ItemReportSerializer(items, many=True).data},
            "Items search results fetched successfully",
        )


class ItemQueryView(APIView):
    """Search and filter items using safe query parameters and cursor pagination."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = request.query_params
        search = params.get("search", "").strip()
        if search and len(search) < 2:
            raise LegacyAPIError(400, "Search must contain at least 2 characters")
        if len(search) > FIELD_MAX_LENGTHS["itemName"]:
            raise LegacyAPIError(400, "Search must be at most 200 characters")

        q = Q(isActive=True)
        if search:
            q &= Q(itemName__icontains=search) | Q(itemSerialNumber__icontains=search)

        category_id = _optional_object_id(params.get("category_id"), "category id")
        subcategory_id = _optional_object_id(params.get("sub_category_id"), "subcategory id")
        room_id = _optional_object_id(params.get("room_id"), "room id")
        floor_id = _optional_object_id(params.get("floor_id"), "floor id")
        department_id = _optional_department_id(params.get("department_id"))
        if category_id:
            q &= Q(itemCategory_id=category_id)
        if subcategory_id:
            q &= Q(itemSubCategory_id=subcategory_id)
        if room_id:
            q &= Q(itemRoom_id=room_id)
        if floor_id:
            q &= Q(itemFloor_id=floor_id)
        if department_id:
            q &= Q(itemFloor__department_id=department_id)

        status = params.get("status", "")
        if status:
            status_map = {"1234": "Working", "3456": "Repairable", "5678": "Not working"}
            status = status_map.get(status, status)
            if status not in dict(Item.Status.choices):
                raise LegacyAPIError(400, "Invalid item status")
            q &= Q(itemStatus=status)

        source = params.get("source", "")
        if source:
            source_map = {"1357": "Purchase", "2468": "Donation"}
            source = source_map.get(source, source)
            if source not in dict(Item.Source.choices):
                raise LegacyAPIError(400, "Invalid item source")
            q &= Q(itemSource=source)

        start_date = params.get("starting_date", "")
        if start_date:
            parsed = parse_date(start_date)
            if parsed is None:
                raise LegacyAPIError(400, "Invalid starting date")
            q &= Q(itemAcquiredDate__gte=parsed)
        end_date = params.get("end_date", "")
        if end_date:
            parsed = parse_date(end_date)
            if parsed is None:
                raise LegacyAPIError(400, "Invalid end date")
            q &= Q(itemAcquiredDate__lte=parsed)

        cursor = _decode_item_cursor(params.get("cursor", ""))
        if cursor:
            updated_at, item_id = cursor
            q &= Q(updated_at__lt=updated_at) | Q(updated_at=updated_at, pk__lt=item_id)

        if params.get("group") == "1":
            return self._grouped_query(request, q, cursor)

        # Fetch one extra row to determine whether a next page exists without COUNT(*).
        results = list(
            Item.objects.filter(q)
            .select_related("itemCategory", "itemSubCategory", "itemFloor", "itemRoom", "createdBy")
            .order_by("-updated_at", "-pk")[: ITEM_QUERY_PAGINATION_LIMIT + 1]
        )
        has_next = len(results) > ITEM_QUERY_PAGINATION_LIMIT
        items = results[:ITEM_QUERY_PAGINATION_LIMIT]
        return api_response(
            200,
            {
                "items": ItemReportSerializer(items, many=True).data,
                "nextCursor": _encode_item_cursor(items[-1]) if has_next else None,
            },
            "Items search results fetched successfully",
        )

    def _grouped_query(self, request, q, cursor):
        """Collapse duplicate items (same name/model/floor/room) into one row with a quantity."""
        from django.db.models import Max

        grouping = (
            Item.objects.filter(q)
            .values("itemName", "itemModelNumberOrMake", "itemFloor_id", "itemRoom_id")
            .annotate(
                quantity=Count("pk"),
                max_updated=Max("updated_at"),
                max_pk=Max("pk"),
            )
            .order_by("-max_updated", "-max_pk")
        )
        if cursor:
            updated_at, item_id = cursor
            grouping = grouping.filter(
                Q(max_updated__lt=updated_at) | Q(max_updated=updated_at, max_pk__lt=item_id)
            )
        groups = list(grouping[: ITEM_QUERY_PAGINATION_LIMIT + 1])
        has_next = len(groups) > ITEM_QUERY_PAGINATION_LIMIT
        groups = groups[:ITEM_QUERY_PAGINATION_LIMIT]

        representatives = {
            item.pk: item
            for item in Item.objects.filter(pk__in=[g["max_pk"] for g in groups])
            .select_related("itemCategory", "itemSubCategory", "itemFloor", "itemRoom", "createdBy")
        }

        items = []
        for g in groups:
            rep = representatives.get(g["max_pk"])
            if rep is None:
                continue
            row = ItemReportSerializer(rep).data
            row["quantity"] = g["quantity"]
            items.append(row)

        if not items:
            raise LegacyAPIError(404, "No items found")
        last = groups[-1]
        next_cursor = None
        if has_next:
            payload = json.dumps(
                {"updated_at": last["max_updated"].isoformat(), "id": last["max_pk"]},
                separators=(",", ":"),
            ).encode("utf-8")
            next_cursor = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        return api_response(
            200,
            {"items": items, "nextCursor": next_cursor},
            "Items grouped search results fetched successfully",
        )


class ItemDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, item_id, action):
        item_id = require_object_id(item_id.strip())

        if action == "status":
            status_id = request.data.get("statusId")
            if not status_id:
                raise LegacyAPIError(400, "Invalid status")
            status_map = {"1234": "Working", "3456": "Repairable", "5678": "Not working"}
            new_status = status_map.get(status_id)
            if not new_status:
                raise LegacyAPIError(403, "Invalid status")
            try:
                item = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                raise LegacyAPIError(404, "Item not found")
            item.itemStatus = new_status
            item.save(update_fields=["itemStatus", "updated_at"])
            log_activity(
                request,
                "Item status updated",
                ActivityLog.EntityType.ITEM,
                entity=item,
                entity_name=item.itemName,
                description=f"Status changed to {new_status}",
            )
            return api_response(200, ItemSerializer(item).data, "Item status updated successfully")

        elif action == "details":
            try:
                item = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                raise LegacyAPIError(404, "Item not found")
            item_name = request.data.get("itemName")
            item_description = request.data.get("itemDescription")
            item_category_id = request.data.get("itemCategory")
            item_sub_category_id = request.data.get("itemSubCategory")
            item_make = request.data.get("itemModelNumberOrMake")
            item_source = request.data.get("itemSource")
            item_cost = request.data.get("itemCost")
            item_acquired_date = request.data.get("itemAcquiredDate")
            item_room_id = request.data.get("itemRoom")
            item_status = request.data.get("itemStatus")

            if item_name is not None:
                check_length(item_name, "itemName")
                item.itemName = item_name.strip() or item.itemName
            if item_description is not None:
                check_length(item_description, "itemDescription")
                item.itemDescription = item_description
            if item_category_id is not None:
                item_category_id = require_object_id(item_category_id.strip())
                if not Category.objects.filter(pk=item_category_id).exists():
                    raise LegacyAPIError(404, "Invalid category")
                item.itemCategory_id = item_category_id
            if item_sub_category_id is not None:
                item_sub_category_id = require_object_id(item_sub_category_id.strip())
                if not SubCategory.objects.filter(pk=item_sub_category_id).exists():
                    raise LegacyAPIError(404, "Invalid subcategory")
                item.itemSubCategory_id = item_sub_category_id
            if item_make is not None:
                check_length(item_make, "itemModelNumberOrMake")
                item.itemModelNumberOrMake = item_make
            if item_source is not None:
                if item_source not in dict(Item.Source.choices):
                    raise LegacyAPIError(404, "Invalid source")
                item.itemSource = item_source
            if item_cost is not None:
                item.itemCost = validate_item_cost(item_cost)
            if item_acquired_date is not None:
                item.itemAcquiredDate = validate_item_acquired_date(item_acquired_date)
            if item_room_id is not None:
                item.itemRoom_id = require_object_id(item_room_id.strip())
                try:
                    room = Room.objects.get(pk=item.itemRoom_id)
                except Room.DoesNotExist:
                    raise LegacyAPIError(404, "Room not found")
                item.itemFloor_id = room.floor_id
            if item_status is not None:
                if item_status not in dict(Item.Status.choices):
                    raise LegacyAPIError(404, "Invalid status")
                item.itemStatus = item_status
            item.save()
            log_activity(
                request,
                "Item details updated",
                ActivityLog.EntityType.ITEM,
                entity=item,
                entity_name=item.itemName,
            )
            return api_response(200, ItemSerializer(item).data, "Item details updated successfully")

        elif action == "room":
            new_room_id = request.data.get("new_room_id")
            if not new_room_id:
                raise LegacyAPIError(400, "Invalid room ID")
            new_room_id = require_object_id(new_room_id.strip())
            try:
                item = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                raise LegacyAPIError(404, "Item not found")
            try:
                room = Room.objects.get(pk=new_room_id)
            except Room.DoesNotExist:
                raise LegacyAPIError(404, "Room not found")
            item.itemRoom_id = new_room_id
            item.itemFloor_id = room.floor_id
            item.save(update_fields=["itemRoom_id", "itemFloor_id", "updated_at"])
            log_activity(
                request,
                "Item room updated",
                ActivityLog.EntityType.ITEM,
                entity=item,
                entity_name=item.itemName,
                description=f"Moved to room {room.roomName}",
            )
            return api_response(200, ItemSerializer(item).data, "Item room updated successfully")

        elif action == "department":
            department_id = request.data.get("new_department_id")
            room_id = request.data.get("new_room_id")
            if not department_id or not room_id:
                raise LegacyAPIError(400, "Department and room are required")
            department_id = require_object_id(department_id.strip())
            room_id = require_object_id(room_id.strip())
            try:
                item = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                raise LegacyAPIError(404, "Item not found")
            try:
                department = Department.objects.get(pk=department_id, isActive=True)
            except Department.DoesNotExist:
                raise LegacyAPIError(404, "Department not found")
            try:
                room = Room.objects.select_related("floor").get(pk=room_id, isActive=True)
            except Room.DoesNotExist:
                raise LegacyAPIError(404, "Room not found")
            if (
                room.floor_id is None
                or not room.floor.isActive
                or room.floor.department_id != department.pk
            ):
                raise LegacyAPIError(
                    400, "Selected room does not belong to the selected department"
                )
            item.itemRoom_id = room.pk
            item.itemFloor_id = room.floor_id
            item.save(update_fields=["itemRoom_id", "itemFloor_id", "updated_at"])
            log_activity(
                request,
                "Item department updated",
                ActivityLog.EntityType.ITEM,
                entity=item,
                entity_name=item.itemName,
                description=(
                    f"Moved to {department.departmentName}, {room.floor.floorName}, "
                    f"room {room.roomName}"
                ),
            )
            return api_response(
                200, ItemSerializer(item).data, "Item department updated successfully"
            )

    def delete(self, request, item_id, action=None):
        item_id = require_object_id(item_id.strip())
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            raise LegacyAPIError(404, "Item not found")
        item.isActive = False
        item.deactivatedAt = datetime.now()
        item.save(update_fields=["isActive", "deactivatedAt", "updated_at"])
        log_activity(
            request,
            "Item deleted",
            ActivityLog.EntityType.ITEM,
            entity=item,
            entity_name=item.itemName,
        )
        return api_response(200, ItemSerializer(item).data, "Item deleted successfully")


class ItemHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        item_id = require_object_id(item_id.strip())
        return api_response(201, [], "Item logs fetched successfully")


class ItemSimilarStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        item_id = require_object_id(item_id.strip())
        try:
            item = Item.objects.get(pk=item_id, isActive=True)
        except Item.DoesNotExist:
            raise LegacyAPIError(404, "Item not found")
        similar = Item.objects.filter(
            isActive=True, itemCategory=item.itemCategory
        ).values("itemModelNumberOrMake").annotate(count=Count("pk")).order_by("-count")
        data = [
            {"modelOrMake": s["itemModelNumberOrMake"] or "", "count": s["count"]}
            for s in similar
        ]
        return api_response(200, data, "Similar items stats fetched successfully")


class ItemFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, category_id, subCategory_id, room_id, floor_id,
            status, source, starting_date, end_date, page):
        q = Q(isActive=True)
        if category_id and category_id != "0":
            q &= Q(itemCategory_id=require_object_id(category_id.strip()))
        if subCategory_id and subCategory_id != "0":
            q &= Q(itemSubCategory_id=require_object_id(subCategory_id.strip()))
        if room_id and room_id != "0":
            q &= Q(itemRoom_id=require_object_id(room_id.strip()))
        if floor_id and floor_id != "0":
            q &= Q(itemFloor_id=require_object_id(floor_id.strip()))
        if status and status != "0":
            status_map = {"1234": "Working", "3456": "Repairable", "5678": "Not working"}
            mapped = status_map.get(status)
            if mapped:
                q &= Q(itemStatus=mapped)
        if source and source != "0":
            source_map = {"1357": "Purchase", "2468": "Donation"}
            mapped = source_map.get(source)
            if mapped:
                q &= Q(itemSource=mapped)
        if starting_date and starting_date != "0":
            parsed = parse_date(starting_date)
            if parsed:
                q &= Q(itemAcquiredDate__gte=parsed)
        if end_date and end_date != "0":
            parsed = parse_date(end_date)
            if parsed:
                q &= Q(itemAcquiredDate__lte=parsed)

        try:
            page_number = int(page) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        start = (page_number - 1) * PAGINATION_LIMIT
        end = page_number * PAGINATION_LIMIT
        total = Item.objects.filter(q).count()
        items = Item.objects.filter(q).select_related(
            "itemCategory", "itemSubCategory", "itemFloor", "itemRoom", "createdBy"
        ).order_by("-updated_at")[start:end]
        return api_response(
            200,
            {"totalItems": total, "items": ItemReportSerializer(items, many=True).data},
            "Filtered items fetched successfully",
        )


class ItemSimilarInstancesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_name, item_model, item_room_id):
        item_room_id = require_object_id(item_room_id.strip())
        q = Q(isActive=True, itemRoom_id=item_room_id, itemName__iexact=item_name)
        if item_model:
            q &= Q(itemModelNumberOrMake__iexact=item_model)
        else:
            q &= Q(itemModelNumberOrMake="")
        items = Item.objects.filter(q).select_related(
            "itemCategory", "itemSubCategory", "itemFloor", "itemRoom", "createdBy"
        )
        return api_response(
            200, ItemReportSerializer(items, many=True).data, "Similar instances fetched successfully"
        )


class ItemBulkView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, action=None):
        item_ids = request.data.get("item_ids", [])
        if not item_ids:
            raise LegacyAPIError(403, "Empty item list")
        for raw_id in item_ids:
            require_object_id(raw_id.strip())
        count = Item.objects.filter(pk__in=item_ids, isActive=True).update(
            isActive=False, deactivatedAt=datetime.now()
        )
        log_activity(
            request,
            "Items deleted",
            ActivityLog.EntityType.ITEM,
            entity_id=None,
            entity_name=None,
            description=f"{count} item(s) deleted",
        )
        return api_response(200, {}, f"{count} items deleted successfully")

    def patch(self, request, action=None):
        item_ids = request.data.get("item_ids", [])
        if not item_ids:
            raise LegacyAPIError(403, "Empty item list")

        if action == "status":
            status_id = request.data.get("statusId")
            status_map = {"1234": "Working", "3456": "Repairable", "5678": "Not working"}
            new_status = status_map.get(status_id)
            if not new_status:
                raise LegacyAPIError(404, "Invalid status")
            for raw_id in item_ids:
                require_object_id(raw_id.strip())
            Item.objects.filter(pk__in=item_ids).update(itemStatus=new_status)
            log_activity(
                request,
                "Bulk status update",
                ActivityLog.EntityType.ITEM,
                description=f"{len(item_ids)} item(s) status changed to {new_status}",
            )
            return api_response(200, {}, "Bulk status update successful")

        elif action == "room":
            new_room_id = request.data.get("new_room_id")
            if not new_room_id:
                raise LegacyAPIError(400, "Invalid room ID")
            new_room_id = require_object_id(new_room_id.strip())
            try:
                room = Room.objects.get(pk=new_room_id)
            except Room.DoesNotExist:
                raise LegacyAPIError(404, "Room not found")
            for raw_id in item_ids:
                require_object_id(raw_id.strip())
            Item.objects.filter(pk__in=item_ids).update(
                itemRoom_id=new_room_id, itemFloor_id=room.floor_id
            )
            log_activity(
                request,
                "Bulk room move",
                ActivityLog.EntityType.ITEM,
                description=f"{len(item_ids)} item(s) moved to room {room.roomName}",
            )
            return api_response(200, {}, "Bulk room move successful")


class ItemCommonView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, page, category_id=None):
        try:
            page_number = int(page) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        start = (page_number - 1) * PAGINATION_LIMIT
        end = page_number * PAGINATION_LIMIT

        q = Q(isActive=True)
        if category_id:
            category_id = require_object_id(category_id.strip())
            q &= Q(itemCategory_id=category_id)

        total = Item.objects.filter(q).values(
            "itemName", "itemCategory", "itemModelNumberOrMake"
        ).annotate(
            working=Count("pk", filter=Q(itemStatus="Working")),
            repairable=Count("pk", filter=Q(itemStatus="Repairable")),
            not_working=Count("pk", filter=Q(itemStatus="Not working")),
        ).count()

        grouped = Item.objects.filter(q).values(
            "itemName", "itemCategory", "itemModelNumberOrMake"
        ).annotate(
            working=Count("pk", filter=Q(itemStatus="Working")),
            repairable=Count("pk", filter=Q(itemStatus="Repairable")),
            not_working=Count("pk", filter=Q(itemStatus="Not working")),
        ).order_by("-working")[start:end]

        data = []
        for g in grouped:
            total_count = g["working"] + g["repairable"] + g["not_working"]
            cat_name = ""
            try:
                cat = Category.objects.get(pk=g["itemCategory"])
                cat_name = cat.categoryName
            except Category.DoesNotExist:
                pass
            data.append({
                "itemName": g["itemName"],
                "itemModel": g["itemModelNumberOrMake"] or "",
                "workingCount": g["working"],
                "repairableCount": g["repairable"],
                "notWorkingCount": g["not_working"],
                "totalCount": total_count,
                "categoryName": cat_name,
                "itemCategoryId": g["itemCategory"],
            })

        if total == 0:
            raise LegacyAPIError(404, "No items found")
        return api_response(
            200,
            {"totalItems": total, "itemData": data},
            "Common items fetched successfully",
        )


class InventoryLogsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, page=None, starting_date=None, end_date=None):
        if page is not None:
            try:
                page_number = int(page) or 1
            except ValueError:
                page_number = 1
            page_number = max(page_number, 1)
            start = (page_number - 1) * PAGINATION_LIMIT
            end_page = page_number * PAGINATION_LIMIT

            q = Q()
            if starting_date and starting_date != "0":
                parsed = parse_date(starting_date)
                if parsed:
                    q &= Q(created_at__date__gte=parsed)
            if end_date and end_date != "0":
                parsed = parse_date(end_date)
                if parsed:
                    q &= Q(created_at__date__lte=parsed)

            total = ActivityLog.objects.filter(q).count()
            logs = ActivityLog.objects.filter(q).order_by("-created_at")[start:end_page]
            return api_response(
                200,
                {"totalLogs": total, "logs": ActivityLogSerializer(logs, many=True).data},
                "Logs fetched successfully",
            )
        return api_response(200, [], "Recent logs fetched successfully")


class InventoryRecentLogsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        logs = ActivityLog.objects.all()[:5]
        if not logs.exists():
            raise LegacyAPIError(404, "No recent logs found")
        return api_response(
            200,
            ActivityLogSerializer(logs, many=True).data,
            "Recent logs fetched successfully",
        )


class InventoryStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # One aggregate query instead of four counts plus a sum query.
        stats = Item.objects.filter(isActive=True).aggregate(
            total=Count("pk"),
            working=Count("pk", filter=Q(itemStatus="Working")),
            repairable=Count("pk", filter=Q(itemStatus="Repairable")),
            not_working=Count("pk", filter=Q(itemStatus="Not working")),
            total_value=Sum("itemCost"),
        )
        return api_response(
            200,
            {
                "no_total_items": stats["total"],
                "no_working": stats["working"],
                "no_repairable": stats["repairable"],
                "no_not_working": stats["not_working"],
                "no_total_items_till_last_month": stats["total"],
                "inventory_total_value": float(stats["total_value"] or 0),
            },
            "Stats fetched successfully",
        )


class InventoryCategoryStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Items without a category are grouped under "Uncategorized".
        rows = (
            Item.objects.filter(isActive=True)
            .values("itemCategory")
            .annotate(totalItems=Count("pk"))
            .order_by("-totalItems")
        )
        cat_ids = [row["itemCategory"] for row in rows if row["itemCategory"]]
        names = dict(
            Category.objects.filter(pk__in=cat_ids).values_list("pk", "categoryName")
        )
        data = [
            {
                "categoryId": row["itemCategory"],
                "categoryName": (
                    names.get(row["itemCategory"], "Uncategorized")
                    if row["itemCategory"]
                    else "Uncategorized"
                ),
                "totalItems": row["totalItems"],
            }
            for row in rows
        ]
        return api_response(200, data, "Category stats fetched successfully")

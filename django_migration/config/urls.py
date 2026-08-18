from django.urls import path, re_path
from django.views.generic import TemplateView

from django.conf import settings
from django.views.static import serve as static_serve

from apps.accounts.views import (
    AccessRequestAdminDetailView,
    AccessRequestCreateView,
    AccessRequestsAdminView,
    ActiveUsersView,
    BlockedRequesterDetailView,
    BlockedRequestersView,
    ChangePasswordView,
    CurrentUserView,
    DeleteUserView,
    EditProfileView,
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
)
from apps.inventory.views import (
    ActivityLogPurgeView,
    CategoryDescriptionView,
    CategoryDetailView,
    CategoryListCreateView,
    FloorDetailView,
    FloorListCreateView,
    DepartmentDetailView,
    DepartmentListCreateView,
    InventoryLogsView,
    InventoryRecentLogsView,
    InventoryStatsView,
    ItemAllView,
    ItemBulkView,
    ItemCommonView,
    ItemCreateView,
    ItemDetailView,
    ItemFilterView,
    ItemHistoryView,
    ItemQueryView,
    ItemSearchView,
    ItemSimilarInstancesView,
    ItemSimilarStatsView,
    ItemSingleView,
    ItemSourceView,
    ItemStatusView,
    RoomCreateView,
    RoomFloorFilterView,
    RoomSearchView,
    RoomView,
    RoomTypeDetailView,
    RoomTypeListCreateView,
    SubCategoryDeleteView,
    SubCategoryDescriptionView,
    SubCategoryListCreateView,
)

urlpatterns = [
    path("api/v1/users/login", LoginView.as_view(), name="login"),
    path("api/v1/users/register", RegisterView.as_view(), name="register"),
    path("api/v1/users/logout", LogoutView.as_view(), name="logout"),
    path(
        "api/v1/users/change-password",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path("api/v1/users/edit-profile", EditProfileView.as_view(), name="edit-profile"),
    path("api/v1/users/active/<str:page>", ActiveUsersView.as_view(), name="active-users"),
    path(
        "api/v1/users/<str:username>/<str:page>",
        ActiveUsersView.as_view(),
        name="search-active-users",
    ),
    path("api/v1/users/refresh", RefreshView.as_view(), name="token-refresh"),
    path("api/v1/users/current-user", CurrentUserView.as_view(), name="current-user"),
    path("api/v1/users/<str:user_id>", DeleteUserView.as_view(), name="delete-user"),
    path(
        "api/v1/access-requests/",
        AccessRequestCreateView.as_view(),
        name="access-request-create",
    ),
    path(
        "api/v1/access-requests/all/",
        AccessRequestsAdminView.as_view(),
        name="access-request-list",
    ),
    path(
        "api/v1/access-requests/<str:request_id>",
        AccessRequestAdminDetailView.as_view(),
        name="access-request-detail",
    ),
    path(
        "api/v1/blocked-requesters/",
        BlockedRequestersView.as_view(),
        name="blocked-requesters",
    ),
    path(
        "api/v1/blocked-requesters/<str:requester_id>",
        BlockedRequesterDetailView.as_view(),
        name="blocked-requester-detail",
    ),
    path("api/v1/floors/", FloorListCreateView.as_view(), name="floor-list-create"),
    path("api/v1/floors/<str:floor_id>", FloorDetailView.as_view(), name="floor-detail"),
    path("api/v1/departments/", DepartmentListCreateView.as_view(), name="department-list-create"),
    path("api/v1/departments/<str:department_id>", DepartmentDetailView.as_view(), name="department-detail"),
    path("api/v1/room-types/", RoomTypeListCreateView.as_view(), name="room-type-list-create"),
    path(
        "api/v1/room-types/<str:room_type_id>",
        RoomTypeDetailView.as_view(),
        name="room-type-detail",
    ),
    path("api/v1/categories/", CategoryListCreateView.as_view(), name="category-list-create"),
    path(
        "api/v1/categories/description/<str:page>",
        CategoryDescriptionView.as_view(),
        name="category-description",
    ),
    path(
        "api/v1/categories/<str:category_id>",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path(
        "api/v1/categories/subcategories/description/<str:category_id>",
        SubCategoryDescriptionView.as_view(),
        name="subcategory-description",
    ),
    path(
        "api/v1/categories/subcategories/<str:category_id>/<str:sub_category_id>",
        SubCategoryDeleteView.as_view(),
        name="subcategory-delete",
    ),
    path(
        "api/v1/categories/subcategories/<str:category_id>",
        SubCategoryListCreateView.as_view(),
        name="subcategory-list-create",
    ),
    path("api/v1/rooms/", RoomCreateView.as_view(), name="room-create"),
    path(
        "api/v1/rooms/floor-filter/<str:floor_id>/<str:page>",
        RoomFloorFilterView.as_view(),
        name="room-floor-filter-page",
    ),
    path(
        "api/v1/rooms/search/<str:room_string>/<str:page>",
        RoomSearchView.as_view(),
        name="room-search",
    ),
    path(
        "api/v1/rooms/floor-filter/<str:floor_id>",
        RoomFloorFilterView.as_view(),
        name="room-floor-filter",
    ),
    path(
        "api/v1/rooms/<str:identifier>",
        RoomView.as_view(),
        name="room-detail",
    ),
    path("api/v1/items/", ItemCreateView.as_view(), name="item-create"),
    path("api/v1/items/item_source", ItemSourceView.as_view(), name="item-source"),
    path("api/v1/items/item_status", ItemStatusView.as_view(), name="item-status"),
    path("api/v1/items/item/<str:item_id>", ItemSingleView.as_view(), name="item-single"),
    path("api/v1/items/all/<str:page>", ItemAllView.as_view(), name="item-all"),
    path("api/v1/items/search", ItemQueryView.as_view(), name="item-query"),
    path(
        "api/v1/items/search/<str:item_string>/<str:page>",
        ItemSearchView.as_view(),
        name="item-search",
    ),
    path("api/v1/items/similar/bulk", ItemBulkView.as_view(), name="item-bulk"),
    path(
        "api/v1/items/similar/<str:item_name>/<str:item_model>/<str:item_room_id>",
        ItemSimilarInstancesView.as_view(),
        name="item-similar-instances",
    ),
    path(
        "api/v1/items/filter/<str:category_id>/<str:subCategory_id>/<str:room_id>/<str:floor_id>/<str:status>/<str:source>/<str:starting_date>/<str:end_date>/<str:page>",
        ItemFilterView.as_view(),
        name="item-filter",
    ),
    path(
        "api/v1/items/common_items/<str:category_id>/<str:page>",
        ItemCommonView.as_view(),
        name="item-common-category",
    ),
    path(
        "api/v1/items/common_items/<str:page>",
        ItemCommonView.as_view(),
        name="item-common",
    ),
    path(
        "api/v1/items/<str:item_id>/status",
        ItemDetailView.as_view(),
        {"action": "status"},
        name="item-status-update",
    ),
    path(
        "api/v1/items/<str:item_id>/details",
        ItemDetailView.as_view(),
        {"action": "details"},
        name="item-details-update",
    ),
    path(
        "api/v1/items/<str:item_id>/room",
        ItemDetailView.as_view(),
        {"action": "room"},
        name="item-room-move",
    ),
    path(
        "api/v1/items/<str:item_id>/history",
        ItemHistoryView.as_view(),
        name="item-history",
    ),
    path(
        "api/v1/items/<str:item_id>/similar_items",
        ItemSimilarStatsView.as_view(),
        name="item-similar-stats",
    ),
    path(
        "api/v1/items/<str:item_id>",
        ItemDetailView.as_view(),
        {"action": "delete"},
        name="item-delete",
    ),
    path(
        "api/v1/inventory/logs/<str:page>/<str:starting_date>/<str:end_date>",
        InventoryLogsView.as_view(),
        name="inventory-logs-dated",
    ),
    path(
        "api/v1/inventory/logs/<str:page>",
        InventoryLogsView.as_view(),
        name="inventory-logs",
    ),
    path(
        "api/v1/inventory/logs/purge/<int:days>",
        ActivityLogPurgeView.as_view(),
        name="inventory-logs-purge",
    ),
    path(
        "api/v1/inventory/recent-logs",
        InventoryRecentLogsView.as_view(),
        name="inventory-recent-logs",
    ),
    path(
        "api/v1/inventory/stats",
        InventoryStatsView.as_view(),
        name="inventory-stats",
    ),
]

# ── Frontend (built SPA) ──────────────────────────────────────────────
FRONTEND_DIST = settings.FRONTEND_DIR / "dist"

urlpatterns += [
    re_path(
        r"^assets/(?P<path>.*)$",
        static_serve,
        {"document_root": str(FRONTEND_DIST / "assets")},
    ),
    re_path(
        r"^(?P<path>favicon\.svg|icons\.svg)$",
        static_serve,
        {"document_root": str(FRONTEND_DIST)},
    ),
]

urlpatterns += [
    re_path(
        r"^(?!api/).*$",
        TemplateView.as_view(template_name="index.html"),
        name="frontend",
    ),
]

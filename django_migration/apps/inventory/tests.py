from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.accounts.testutils import SecurityAwareAPITestCase
from .models import ActivityLog, Category, Department, Floor, Item, Room, RoomType, SubCategory


def assert_legacy_error(response, expected_status):
    assert response.status_code == expected_status
    assert response.data["statusCode"] == expected_status
    assert response.data["success"] is False
    assert response.data["data"] is None


class FloorResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin_password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.admin_password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="regular",
            email="user@example.com",
            password="another-safe-password",
            phone_number="9811111111",
            role=User.Role.USER,
        )

    def _login(self, username="admin", password=None):
        response = self.client.post(
            "/api/v1/users/login",
            {"username": username, "password": password or self.admin_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def _auth_as_admin(self):
        login = self._login()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}"
        )
        return login

    def _auth_as_user(self):
        login = self._login(
            username="regular", password="another-safe-password"
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}"
        )
        return login

    def test_floor_model_shape(self):
        self.assertEqual(len(self.admin.pk), 24)
        floor = Floor.objects.create(
            floorName="Ground Floor",
            createdBy=self.admin,
            floorNameNormalized="ground floor",
        )
        self.assertEqual(floor.floorName, "Ground Floor")
        self.assertTrue(floor.isActive)
        self.assertEqual(floor.floorNameNormalized, "ground floor")
        self.assertEqual(len(floor.pk), 24)
        self.assertIsNotNone(floor.created_at)
        self.assertIsNotNone(floor.updated_at)
        self.assertEqual(
            Floor._meta.get_field("createdBy").remote_field.on_delete.__name__,
            "SET_NULL",
        )

    def test_create_floor_as_admin(self):
        self._auth_as_admin()
        response = self.client.post(
            "/api/v1/floors/", {"floorName": "First Floor"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["floorName"], "First Floor")
        self.assertEqual(response.data["data"]["createdBy"], self.admin.pk)

    def test_create_floor_requires_admin(self):
        self._auth_as_user()
        response = self.client.post(
            "/api/v1/floors/", {"floorName": "First Floor"}, format="json"
        )
        assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_create_floor_requires_auth(self):
        response = self.client.post(
            "/api/v1/floors/", {"floorName": "First Floor"}, format="json"
        )
        assert_legacy_error(response, status.HTTP_401_UNAUTHORIZED)

    def test_create_floor_duplicate_normalized_name(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/floors/", {"floorName": "First Floor"}, format="json"
        )
        response = self.client.post(
            "/api/v1/floors/", {"floorName": "first floor"}, format="json"
        )
        assert_legacy_error(response, status.HTTP_409_CONFLICT)

    def test_list_floors(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/floors/", {"floorName": "First Floor"}, format="json"
        )
        self.client.post(
            "/api/v1/floors/", {"floorName": "Second Floor"}, format="json"
        )
        response = self.client.get("/api/v1/floors/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertIn("_id", response.data["data"][0])
        self.assertIn("floorName", response.data["data"][0])
        self.assertNotIn("createdBy", response.data["data"][0])

    def test_list_floors_empty_returns_404(self):
        self._auth_as_admin()
        response = self.client.get("/api/v1/floors/")
        assert_legacy_error(response, status.HTTP_404_NOT_FOUND)

    def test_update_floor_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/floors/", {"floorName": "Old Name"}, format="json"
        ).data["data"]
        response = self.client.patch(
            f"/api/v1/floors/{created['_id']}",
            {"floorName": "New Name"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["floorName"], "New Name")

    def test_update_floor_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/floors/", {"floorName": "Old Name"}, format="json"
        ).data["data"]
        self._auth_as_user()
        response = self.client.patch(
            f"/api/v1/floors/{created['_id']}",
            {"floorName": "New Name"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_update_floor_not_found(self):
        self._auth_as_admin()
        response = self.client.patch(
            "/api/v1/floors/aaaaaaaaaaaaaaaaaaaaaaaa",
            {"floorName": "New Name"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_404_NOT_FOUND)

    def test_update_floor_duplicate_name(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/floors/", {"floorName": "First"}, format="json"
        )
        second = self.client.post(
            "/api/v1/floors/", {"floorName": "Second"}, format="json"
        ).data["data"]
        response = self.client.patch(
            f"/api/v1/floors/{second['_id']}",
            {"floorName": "first"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_409_CONFLICT)

    def test_update_floor_invalid_object_id(self):
        self._auth_as_admin()
        response = self.client.patch(
            "/api/v1/floors/not-an-id",
            {"floorName": "New Name"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)

    def test_delete_floor_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/floors/", {"floorName": "To Delete"}, format="json"
        ).data["data"]
        response = self.client.delete(f"/api/v1/floors/{created['_id']}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], {})

    def test_delete_floor_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/floors/", {"floorName": "To Delete"}, format="json"
        ).data["data"]
        self._auth_as_user()
        response = self.client.delete(f"/api/v1/floors/{created['_id']}")
        assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_delete_floor_already_inactive(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/floors/", {"floorName": "To Delete"}, format="json"
        ).data["data"]
        self.client.delete(f"/api/v1/floors/{created['_id']}")
        response = self.client.delete(f"/api/v1/floors/{created['_id']}")
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)

    def test_delete_floor_not_found(self):
        self._auth_as_admin()
        response = self.client.delete(
            "/api/v1/floors/aaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert_legacy_error(response, status.HTTP_404_NOT_FOUND)

    def test_delete_floor_invalid_object_id(self):
        self._auth_as_admin()
        response = self.client.delete("/api/v1/floors/bad-id")
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)


class RoomTypeResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="correct-horse-battery-staple",
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="regular",
            email="user@example.com",
            password="another-safe-password",
            phone_number="9811111111",
            role=User.Role.USER,
        )

    def _login(self, username="admin", password=None):
        response = self.client.post(
            "/api/v1/users/login",
            {"username": username, "password": password or "correct-horse-battery-staple"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def _auth_as_admin(self):
        login = self._login()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}"
        )
        return login

    def _auth_as_user(self):
        login = self._login(username="regular", password="another-safe-password")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}"
        )
        return login

    def test_room_type_model_shape(self):
        rt = RoomType.objects.create(
            roomTypeName="Lab",
            createdBy=self.admin,
            roomTypeNameNormalized="lab",
        )
        self.assertEqual(rt.roomTypeName, "Lab")
        self.assertTrue(rt.isActive)
        self.assertEqual(rt.roomTypeNameNormalized, "lab")
        self.assertEqual(len(rt.pk), 24)
        self.assertIsNotNone(rt.created_at)
        self.assertEqual(
            RoomType._meta.get_field("createdBy").remote_field.on_delete.__name__,
            "SET_NULL",
        )

    def test_create_room_type_as_admin(self):
        self._auth_as_admin()
        response = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Lab"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["roomTypeName"], "Lab")

    def test_create_room_type_requires_admin(self):
        self._auth_as_user()
        response = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Lab"}, format="json"
        )
        assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_create_room_type_requires_name(self):
        self._auth_as_admin()
        response = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": ""}, format="json"
        )
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)

    def test_create_room_type_duplicate(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Lab"}, format="json"
        )
        response = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "lab"}, format="json"
        )
        assert_legacy_error(response, status.HTTP_409_CONFLICT)

    def test_list_room_types(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Lab"}, format="json"
        )
        self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Classroom"}, format="json"
        )
        response = self.client.get("/api/v1/room-types/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertIn("_id", response.data["data"][0])
        self.assertIn("roomTypeName", response.data["data"][0])

    def test_list_room_types_empty_returns_404(self):
        self._auth_as_admin()
        response = self.client.get("/api/v1/room-types/")
        assert_legacy_error(response, status.HTTP_404_NOT_FOUND)

    def test_update_room_type_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Old"}, format="json"
        ).data["data"]
        response = self.client.patch(
            f"/api/v1/room-types/{created['_id']}",
            {"roomTypeName": "New"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["roomTypeName"], "New")

    def test_update_room_type_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Old"}, format="json"
        ).data["data"]
        self._auth_as_user()
        response = self.client.patch(
            f"/api/v1/room-types/{created['_id']}",
            {"roomTypeName": "New"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_update_room_type_empty_name(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Old"}, format="json"
        ).data["data"]
        response = self.client.patch(
            f"/api/v1/room-types/{created['_id']}",
            {"roomTypeName": ""},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)

    def test_update_room_type_not_found(self):
        self._auth_as_admin()
        response = self.client.patch(
            "/api/v1/room-types/aaaaaaaaaaaaaaaaaaaaaaaa",
            {"roomTypeName": "New"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_404_NOT_FOUND)

    def test_update_room_type_duplicate(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Lab"}, format="json"
        )
        second = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "Classroom"}, format="json"
        ).data["data"]
        response = self.client.patch(
            f"/api/v1/room-types/{second['_id']}",
            {"roomTypeName": "lab"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_409_CONFLICT)

    def test_update_room_type_invalid_object_id(self):
        self._auth_as_admin()
        response = self.client.patch(
            "/api/v1/room-types/bad-id",
            {"roomTypeName": "New"},
            format="json",
        )
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)

    def test_delete_room_type_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "To Delete"}, format="json"
        ).data["data"]
        response = self.client.delete(f"/api/v1/room-types/{created['_id']}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], {})

    def test_delete_room_type_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "To Delete"}, format="json"
        ).data["data"]
        self._auth_as_user()
        response = self.client.delete(f"/api/v1/room-types/{created['_id']}")
        assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_delete_room_type_already_inactive(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/room-types/", {"roomTypeName": "To Delete"}, format="json"
        ).data["data"]
        self.client.delete(f"/api/v1/room-types/{created['_id']}")
        response = self.client.delete(f"/api/v1/room-types/{created['_id']}")
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)

    def test_delete_room_type_not_found(self):
        self._auth_as_admin()
        response = self.client.delete(
            "/api/v1/room-types/aaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert_legacy_error(response, status.HTTP_404_NOT_FOUND)

    def test_delete_room_type_invalid_object_id(self):
        self._auth_as_admin()
        response = self.client.delete("/api/v1/room-types/bad-id")
        assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)


class CategoryResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="correct-horse-battery-staple",
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="regular",
            email="user@example.com",
            password="another-safe-password",
            phone_number="9811111111",
            role=User.Role.USER,
        )

    def _login(self, username="admin", password=None):
        r = self.client.post(
            "/api/v1/users/login",
            {"username": username, "password": password or "correct-horse-battery-staple"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        return r

    def _auth_as_admin(self):
        login = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def _auth_as_user(self):
        login = self._login(username="regular", password="another-safe-password")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def test_category_model_shape(self):
        cat = Category.objects.create(
            categoryName="Electronics",
            createdBy=self.admin,
            categoryNameNormalized="electronics",
        )
        self.assertEqual(cat.categoryName, "Electronics")
        self.assertTrue(cat.isActive)
        self.assertEqual(cat.categoryNameNormalized, "electronics")
        self.assertEqual(len(cat.pk), 24)
        self.assertEqual(
            Category._meta.get_field("createdBy").remote_field.on_delete.__name__,
            "SET_NULL",
        )

    def test_create_category_as_admin(self):
        self._auth_as_admin()
        r = self.client.post(
            "/api/v1/categories/", {"categoryName": "Electronics"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["categoryName"], "Electronics")

    def test_create_category_requires_admin(self):
        self._auth_as_user()
        r = self.client.post(
            "/api/v1/categories/", {"categoryName": "Electronics"}, format="json"
        )
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_create_category_requires_non_blank_name(self):
        self._auth_as_admin()
        r = self.client.post("/api/v1/categories/", {"categoryName": ""}, format="json")
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_create_category_duplicate_normalized_name(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/categories/", {"categoryName": "Electronics"}, format="json"
        )
        r = self.client.post(
            "/api/v1/categories/", {"categoryName": "electronics"}, format="json"
        )
        assert_legacy_error(r, status.HTTP_409_CONFLICT)

    def test_list_categories_returns_array_even_when_empty(self):
        self._auth_as_admin()
        r = self.client.get("/api/v1/categories/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"], [])

    def test_list_categories(self):
        self._auth_as_admin()
        self.client.post("/api/v1/categories/", {"categoryName": "A"}, format="json")
        self.client.post("/api/v1/categories/", {"categoryName": "B"}, format="json")
        r = self.client.get("/api/v1/categories/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]), 2)
        self.assertIn("categoryName", r.data["data"][0])

    def test_update_category_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/categories/", {"categoryName": "Old"}, format="json"
        ).data["data"]
        r = self.client.patch(
            f"/api/v1/categories/{created['_id']}",
            {"categoryName": "New"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["categoryName"], "New")

    def test_update_category_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/categories/", {"categoryName": "Old"}, format="json"
        ).data["data"]
        self._auth_as_user()
        r = self.client.patch(
            f"/api/v1/categories/{created['_id']}",
            {"categoryName": "New"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_update_category_not_found(self):
        self._auth_as_admin()
        r = self.client.patch(
            "/api/v1/categories/aaaaaaaaaaaaaaaaaaaaaaaa",
            {"categoryName": "New"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_update_category_empty_name(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/categories/", {"categoryName": "Old"}, format="json"
        ).data["data"]
        r = self.client.patch(
            f"/api/v1/categories/{created['_id']}",
            {"categoryName": ""},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_update_category_duplicate_name(self):
        self._auth_as_admin()
        self.client.post("/api/v1/categories/", {"categoryName": "First"}, format="json")
        second = self.client.post(
            "/api/v1/categories/", {"categoryName": "Second"}, format="json"
        ).data["data"]
        r = self.client.patch(
            f"/api/v1/categories/{second['_id']}",
            {"categoryName": "first"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_409_CONFLICT)

    def test_update_category_invalid_object_id(self):
        self._auth_as_admin()
        r = self.client.patch(
            "/api/v1/categories/bad-id",
            {"categoryName": "New"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_delete_category_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/categories/", {"categoryName": "To Delete"}, format="json"
        ).data["data"]
        r = self.client.delete(f"/api/v1/categories/{created['_id']}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"], {})

    def test_delete_category_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/categories/", {"categoryName": "To Delete"}, format="json"
        ).data["data"]
        self._auth_as_user()
        r = self.client.delete(f"/api/v1/categories/{created['_id']}")
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_delete_category_already_inactive(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/categories/", {"categoryName": "To Delete"}, format="json"
        ).data["data"]
        self.client.delete(f"/api/v1/categories/{created['_id']}")
        r = self.client.delete(f"/api/v1/categories/{created['_id']}")
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_delete_category_not_found(self):
        self._auth_as_admin()
        r = self.client.delete("/api/v1/categories/aaaaaaaaaaaaaaaaaaaaaaaa")
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_delete_category_invalid_object_id(self):
        self._auth_as_admin()
        r = self.client.delete("/api/v1/categories/bad-id")
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_category_description_empty(self):
        self._auth_as_admin()
        r = self.client.get("/api/v1/categories/description/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalCategories"], 0)
        self.assertEqual(r.data["data"]["categories"], [])

    def test_category_description_paginated(self):
        self._auth_as_admin()
        for i in range(8):
            self.client.post(
                "/api/v1/categories/", {"categoryName": f"Cat{i}"}, format="json"
            )
        r = self.client.get("/api/v1/categories/description/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalCategories"], 8)
        self.assertEqual(len(r.data["data"]["categories"]), 6)
        self.assertIn("creatorUsername", r.data["data"]["categories"][0])


class SubCategoryResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com",
            password="correct-horse-battery-staple", phone_number="9800000000",
            role=User.Role.ADMIN, is_staff=True,
        )
        self.user = User.objects.create_user(
            username="regular", email="user@example.com",
            password="another-safe-password", phone_number="9811111111",
            role=User.Role.USER,
        )
        self.category = Category.objects.create(
            categoryName="TestCat", createdBy=self.admin, categoryNameNormalized="testcat",
        )

    def _login(self, username="admin", password=None):
        r = self.client.post(
            "/api/v1/users/login",
            {"username": username, "password": password or "correct-horse-battery-staple"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        return r

    def _auth_as_admin(self):
        login = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def _auth_as_user(self):
        login = self._login(username="regular", password="another-safe-password")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def test_subcategory_model_shape(self):
        sc = SubCategory.objects.create(
            subCategoryName="Monitor", subCategoryAbbreviation="MON",
            createdBy=self.admin, category=self.category,
            subCategoryNameNormalized="monitor", subCategoryAbbreviationNormalized="mon",
        )
        self.assertEqual(sc.subCategoryName, "Monitor")
        self.assertEqual(sc.subCategoryAbbreviation, "MON")
        self.assertEqual(sc.lastItemSerialNumber, 0)
        self.assertTrue(sc.isActive)
        self.assertEqual(sc.category_id, self.category.pk)
        self.assertEqual(len(sc.pk), 24)
        self.assertEqual(
            SubCategory._meta.get_field("createdBy").remote_field.on_delete.__name__, "SET_NULL",
        )

    def test_create_subcategory_as_admin(self):
        self._auth_as_admin()
        r = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "Monitor", "subCategoryAbbreviation": "MON"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["subCategoryName"], "Monitor")
        self.assertEqual(r.data["data"]["subCategoryAbbreviation"], "MON")

    def test_create_subcategory_requires_admin(self):
        self._auth_as_user()
        r = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "Monitor", "subCategoryAbbreviation": "MON"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_create_subcategory_requires_both_fields(self):
        self._auth_as_admin()
        r = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "", "subCategoryAbbreviation": ""},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_create_subcategory_category_not_found(self):
        self._auth_as_admin()
        r = self.client.post(
            "/api/v1/categories/subcategories/aaaaaaaaaaaaaaaaaaaaaaaa",
            {"subCategoryName": "Monitor", "subCategoryAbbreviation": "MON"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_create_subcategory_duplicate_name(self):
        self._auth_as_admin()
        self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "Monitor", "subCategoryAbbreviation": "MON"},
            format="json",
        )
        r = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "monitor", "subCategoryAbbreviation": "MON2"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_409_CONFLICT)

    def test_create_subcategory_duplicate_abbreviation(self):
        self._auth_as_admin()
        self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "Monitor", "subCategoryAbbreviation": "MON"},
            format="json",
        )
        r = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "Display", "subCategoryAbbreviation": "mon"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_409_CONFLICT)

    def test_list_subcategories(self):
        self._auth_as_admin()
        self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "A", "subCategoryAbbreviation": "A1"},
            format="json",
        )
        self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "B", "subCategoryAbbreviation": "B1"},
            format="json",
        )
        r = self.client.get(f"/api/v1/categories/subcategories/{self.category.pk}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]), 2)
        self.assertIn("subCategoryName", r.data["data"][0])

    def test_delete_subcategory_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "To Delete", "subCategoryAbbreviation": "DEL"},
            format="json",
        ).data["data"]
        r = self.client.delete(
            f"/api/v1/categories/subcategories/{self.category.pk}/{created['_id']}"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"], {})

    def test_delete_subcategory_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "To Delete", "subCategoryAbbreviation": "DEL"},
            format="json",
        ).data["data"]
        self._auth_as_user()
        r = self.client.delete(
            f"/api/v1/categories/subcategories/{self.category.pk}/{created['_id']}"
        )
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_delete_subcategory_already_inactive(self):
        self._auth_as_admin()
        created = self.client.post(
            f"/api/v1/categories/subcategories/{self.category.pk}",
            {"subCategoryName": "To Delete", "subCategoryAbbreviation": "DEL"},
            format="json",
        ).data["data"]
        self.client.delete(
            f"/api/v1/categories/subcategories/{self.category.pk}/{created['_id']}"
        )
        r = self.client.delete(
            f"/api/v1/categories/subcategories/{self.category.pk}/{created['_id']}"
        )
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_delete_subcategory_category_not_found(self):
        self._auth_as_admin()
        r = self.client.delete(
            "/api/v1/categories/subcategories/aaaaaaaaaaaaaaaaaaaaaaaa/bbbbbbbbbbbbbbbbbbbbbbbb"
        )
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_delete_subcategory_not_found(self):
        self._auth_as_admin()
        r = self.client.delete(
            f"/api/v1/categories/subcategories/{self.category.pk}/aaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_delete_subcategory_invalid_object_id(self):
        self._auth_as_admin()
        r = self.client.delete(
            f"/api/v1/categories/subcategories/{self.category.pk}/bad-id"
        )
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_subcategory_description_empty(self):
        self._auth_as_admin()
        r = self.client.get(
            f"/api/v1/categories/subcategories/description/{self.category.pk}"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalSubCategories"], 0)
        self.assertEqual(r.data["data"]["subCategories"], [])


class RoomResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com",
            password="correct-horse-battery-staple", phone_number="9800000000",
            role=User.Role.ADMIN, is_staff=True,
        )
        self.user = User.objects.create_user(
            username="regular", email="user@example.com",
            password="another-safe-password", phone_number="9811111111",
            role=User.Role.USER,
        )
        self.floor = Floor.objects.create(
            floorName="Ground", createdBy=self.admin, floorNameNormalized="ground",
        )
        self.room_type = RoomType.objects.create(
            roomTypeName="Lab", createdBy=self.admin, roomTypeNameNormalized="lab",
        )

    def _login(self, username="admin", password=None):
        r = self.client.post(
            "/api/v1/users/login",
            {"username": username, "password": password or "correct-horse-battery-staple"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        return r

    def _auth_as_admin(self):
        login = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def _auth_as_user(self):
        login = self._login(username="regular", password="another-safe-password")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def test_room_model_shape(self):
        r = Room.objects.create(
            roomName="CS101", floor=self.floor, roomType=self.room_type,
            createdBy=self.admin, roomNameNormalized="cs101",
        )
        self.assertEqual(r.roomName, "CS101")
        self.assertTrue(r.isActive)
        self.assertIsNone(r.allottedTo)
        self.assertEqual(r.floor_id, self.floor.pk)
        self.assertEqual(r.roomType_id, self.room_type.pk)
        self.assertEqual(len(r.pk), 24)
        self.assertEqual(
            Room._meta.get_field("floor").remote_field.on_delete.__name__, "SET_NULL",
        )

    def test_create_room_as_admin(self):
        self._auth_as_admin()
        r = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "CS101", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["roomName"], "CS101")

    def test_create_room_requires_admin(self):
        self._auth_as_user()
        r = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "CS101", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_create_room_insufficient_body(self):
        self._auth_as_admin()
        r = self.client.post("/api/v1/rooms/", {"room_name": "CS101"}, format="json")
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_create_room_floor_not_found(self):
        self._auth_as_admin()
        r = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "CS101", "room_floor_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
             "room_type_id": self.room_type.pk},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_create_room_type_not_found(self):
        self._auth_as_admin()
        r = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "CS101", "room_floor_id": self.floor.pk,
             "room_type_id": "aaaaaaaaaaaaaaaaaaaaaaaa"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_create_room_duplicate(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/rooms/",
            {"room_name": "CS101", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        )
        r = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "CS101", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_409_CONFLICT)

    def test_list_rooms_empty(self):
        self._auth_as_admin()
        r = self.client.get("/api/v1/rooms/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalRooms"], 0)

    def test_list_rooms_with_data(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/rooms/",
            {"room_name": "R1", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        )
        r = self.client.get("/api/v1/rooms/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalRooms"], 1)
        self.assertIn("roomFloorName", r.data["data"]["rooms"][0])

    def test_update_room_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "Old", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        ).data["data"]
        r = self.client.patch(
            f"/api/v1/rooms/{created['_id']}",
            {"room_name": "New"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["roomName"], "New")

    def test_update_room_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "Old", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        ).data["data"]
        self._auth_as_user()
        r = self.client.patch(
            f"/api/v1/rooms/{created['_id']}",
            {"room_name": "New"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_update_room_not_found(self):
        self._auth_as_admin()
        r = self.client.patch(
            "/api/v1/rooms/aaaaaaaaaaaaaaaaaaaaaaaa",
            {"room_name": "New"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_update_room_no_fields(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "Old", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        ).data["data"]
        r = self.client.patch(
            f"/api/v1/rooms/{created['_id']}", {}, format="json"
        )
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_update_room_duplicate_name(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/rooms/",
            {"room_name": "First", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        )
        second = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "Second", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        ).data["data"]
        r = self.client.patch(
            f"/api/v1/rooms/{second['_id']}",
            {"room_name": "first"},
            format="json",
        )
        assert_legacy_error(r, status.HTTP_409_CONFLICT)

    def test_delete_room_as_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "To Del", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        ).data["data"]
        r = self.client.delete(f"/api/v1/rooms/{created['_id']}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"], {})

    def test_delete_room_requires_admin(self):
        self._auth_as_admin()
        created = self.client.post(
            "/api/v1/rooms/",
            {"room_name": "To Del", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        ).data["data"]
        self._auth_as_user()
        r = self.client.delete(f"/api/v1/rooms/{created['_id']}")
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_delete_room_not_found(self):
        self._auth_as_admin()
        r = self.client.delete("/api/v1/rooms/aaaaaaaaaaaaaaaaaaaaaaaa")
        assert_legacy_error(r, status.HTTP_404_NOT_FOUND)

    def test_room_floor_filter_paginated(self):
        self._auth_as_admin()
        other_floor = Floor.objects.create(
            floorName="First", createdBy=self.admin, floorNameNormalized="first",
        )
        self.client.post(
            "/api/v1/rooms/",
            {"room_name": "A", "room_floor_id": self.floor.pk, "room_type_id": self.room_type.pk},
            format="json",
        )
        self.client.post(
            "/api/v1/rooms/",
            {"room_name": "B", "room_floor_id": other_floor.pk, "room_type_id": self.room_type.pk},
            format="json",
        )
        r = self.client.get(f"/api/v1/rooms/floor-filter/{self.floor.pk}/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalRooms"], 1)

    def test_room_floor_filter_simple(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/rooms/",
            {"room_name": "A", "room_floor_id": self.floor.pk, "room_type_id": self.room_type.pk},
            format="json",
        )
        r = self.client.get(f"/api/v1/rooms/floor-filter/{self.floor.pk}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]), 1)
        self.assertIn("roomName", r.data["data"][0])

    def test_room_search(self):
        self._auth_as_admin()
        self.client.post(
            "/api/v1/rooms/",
            {"room_name": "Server Room", "room_floor_id": self.floor.pk,
             "room_type_id": self.room_type.pk},
            format="json",
        )
        r = self.client.get("/api/v1/rooms/search/Server/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalRooms"], 1)


class ItemResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com",
            password="correct-horse-battery-staple", phone_number="9800000000",
            role=User.Role.ADMIN, is_staff=True,
        )
        self.user = User.objects.create_user(
            username="regular", email="user@example.com",
            password="another-safe-password", phone_number="9811111111",
            role=User.Role.USER,
        )
        self.floor = Floor.objects.create(
            floorName="Ground", createdBy=self.admin, floorNameNormalized="ground",
        )
        self.room_type = RoomType.objects.create(
            roomTypeName="Lab", createdBy=self.admin, roomTypeNameNormalized="lab",
        )
        self.room = Room.objects.create(
            roomName="R101", floor=self.floor, roomType=self.room_type,
            createdBy=self.admin, roomNameNormalized="r101",
        )
        self.category = Category.objects.create(
            categoryName="Electronics", createdBy=self.admin, categoryNameNormalized="electronics",
        )
        self.sub_category = SubCategory.objects.create(
            subCategoryName="Monitor", subCategoryAbbreviation="MON",
            createdBy=self.admin, category=self.category,
            subCategoryNameNormalized="monitor", subCategoryAbbreviationNormalized="mon",
        )

    def _login(self, username="admin", password=None):
        r = self.client.post(
            "/api/v1/users/login",
            {"username": username, "password": password or "correct-horse-battery-staple"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        return r

    def _auth_as_admin(self):
        login = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def _auth_as_user(self):
        login = self._login(username="regular", password="another-safe-password")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        return login

    def test_item_model_shape(self):
        item = Item.objects.create(
            itemName="Dell Monitor", itemCategory=self.category,
            itemSubCategory=self.sub_category, itemFloor=self.floor,
            itemRoom=self.room, itemStatus="Working", itemSource="Purchase",
            itemCost=15000, itemAcquiredDate="2026-01-15",
            itemSerialNumber="2026MON001", createdBy=self.admin,
        )
        self.assertEqual(item.itemName, "Dell Monitor")
        self.assertEqual(item.itemStatus, "Working")
        self.assertEqual(item.itemSource, "Purchase")
        self.assertTrue(item.isActive)
        self.assertIsNone(item.deactivatedAt)
        self.assertEqual(len(item.pk), 24)

    def test_create_item_as_admin(self):
        self._auth_as_admin()
        r = self.client.post("/api/v1/items/", {
            "itemName": "Dell Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 15000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"][0]["itemName"], "Dell Monitor")

    def test_create_item_requires_admin(self):
        self._auth_as_user()
        r = self.client.post("/api/v1/items/", {
            "itemName": "Dell Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 15000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json")
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)

    def test_create_item_missing_fields(self):
        self._auth_as_admin()
        r = self.client.post("/api/v1/items/", {
            "itemName": "Dell Monitor",
        }, format="json")
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_within_limit_creates_multiple(self):
        self._auth_as_admin()
        r = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 15000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
            "item_create_count": 3,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(r.data["data"]), 3)

    def test_bulk_create_rejects_count_over_cap(self):
        self._auth_as_admin()
        r = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 15000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
            "item_create_count": "101",
        }, format="json")
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_rejects_non_numeric_and_zero_count(self):
        self._auth_as_admin()
        payload = {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 15000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }
        for bad in ("abc", "1e3", "-1", "0"):
            r = self.client.post(
                "/api/v1/items/", {**payload, "item_create_count": bad}, format="json"
            )
            assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_item_source_and_status_endpoints(self):
        self._auth_as_admin()
        r = self.client.get("/api/v1/items/item_source")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]), 2)
        r = self.client.get("/api/v1/items/item_status")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]), 3)

    def test_update_item_status(self):
        self._auth_as_admin()
        created = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 10000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]
        r = self.client.patch(
            f"/api/v1/items/{created['_id']}/status",
            {"statusId": "3456"}, format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["itemStatus"], "Repairable")

    def test_delete_item(self):
        self._auth_as_admin()
        created = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 10000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]
        r = self.client.delete(f"/api/v1/items/{created['_id']}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["data"]["isActive"])
        self.assertIsNotNone(r.data["data"]["deactivatedAt"])

    def test_list_all_items(self):
        self._auth_as_admin()
        self.client.post("/api/v1/items/", {
            "itemName": "A", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 100,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json")
        r = self.client.get("/api/v1/items/all/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalItems"], 1)

    def test_get_single_item(self):
        self._auth_as_admin()
        created = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 10000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]
        r = self.client.get(f"/api/v1/items/item/{created['_id']}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["itemName"], "Monitor")

    def test_search_items(self):
        self._auth_as_admin()
        self.client.post("/api/v1/items/", {
            "itemName": "Dell Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 10000,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json")
        r = self.client.get("/api/v1/items/search/Monitor/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalItems"], 1)

    def test_item_query_combines_text_and_structured_filters(self):
        self._auth_as_admin()
        Item.objects.create(
            itemName="AC/DC Monitor", itemCategory=self.category,
            itemSubCategory=self.sub_category, itemFloor=self.floor,
            itemRoom=self.room, itemStatus="Working", itemSource="Purchase",
            itemCost=100, itemAcquiredDate="2026-01-15", itemSerialNumber="AC/DC-1",
        )
        Item.objects.create(
            itemName="AC/DC Monitor", itemCategory=self.category,
            itemSubCategory=self.sub_category, itemFloor=self.floor,
            itemRoom=self.room, itemStatus="Working", itemSource="Donation",
            itemCost=100, itemAcquiredDate="2026-01-15", itemSerialNumber="AC/DC-2",
        )
        r = self.client.get(
            "/api/v1/items/search",
            {"search": "AC/DC", "floor_id": self.floor.pk, "source": "1357"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]["items"]), 1)
        self.assertEqual(r.data["data"]["items"][0]["itemSource"], "Purchase")

    def test_item_query_rejects_short_search_and_invalid_cursor(self):
        self._auth_as_admin()
        r = self.client.get("/api/v1/items/search", {"search": "A"})
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)
        r = self.client.get("/api/v1/items/search", {"cursor": "not-a-cursor"})
        assert_legacy_error(r, status.HTTP_400_BAD_REQUEST)

    def test_item_query_uses_cursor_without_duplicate_results(self):
        self._auth_as_admin()
        for number in range(7):
            Item.objects.create(
                itemName=f"Monitor {number}", itemCategory=self.category,
                itemSubCategory=self.sub_category, itemFloor=self.floor,
                itemRoom=self.room, itemStatus="Working", itemSource="Purchase",
                itemCost=100, itemAcquiredDate="2026-01-15", itemSerialNumber=f"MON-{number}",
            )
        first = self.client.get("/api/v1/items/search", {"search": "Monitor"})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        first_items = first.data["data"]["items"]
        self.assertEqual(len(first_items), 6)
        cursor = first.data["data"]["nextCursor"]
        self.assertIsNotNone(cursor)
        second = self.client.get("/api/v1/items/search", {"search": "Monitor", "cursor": cursor})
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        second_items = second.data["data"]["items"]
        self.assertEqual(len(second_items), 1)
        self.assertFalse({item["_id"] for item in first_items} & {item["_id"] for item in second_items})

    def test_item_query_group_collapses_duplicates_with_quantity(self):
        self._auth_as_admin()
        for _ in range(12):
            Item.objects.create(
                itemName="HP Computer", itemCategory=self.category,
                itemSubCategory=self.sub_category, itemFloor=self.floor,
                itemRoom=self.room, itemStatus="Working", itemSource="Purchase",
                itemCost=100, itemAcquiredDate="2026-01-15", itemSerialNumber="HP-1",
            )
        r = self.client.get("/api/v1/items/search", {"group": "1"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.data["data"]
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 12)
        self.assertEqual(data["items"][0]["itemName"], "HP Computer")

    def test_update_item_details(self):
        self._auth_as_admin()
        created = self.client.post("/api/v1/items/", {
            "itemName": "Old", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 100,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]
        r = self.client.patch(
            f"/api/v1/items/{created['_id']}/details",
            {"itemName": "New Name"}, format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["itemName"], "New Name")

    def test_item_history(self):
        self._auth_as_admin()
        created = self.client.post("/api/v1/items/", {
            "itemName": "Test", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 100,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]
        r = self.client.get(f"/api/v1/items/{created['_id']}/history")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"], [])

    def test_item_similar_stats(self):
        self._auth_as_admin()
        created = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 100,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]
        r = self.client.get(f"/api/v1/items/{created['_id']}/similar_items")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]), 1)

    def test_move_item_room(self):
        self._auth_as_admin()
        other_room = Room.objects.create(
            roomName="R102", floor=self.floor, roomType=self.room_type,
            createdBy=self.admin, roomNameNormalized="r102",
        )
        created = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 100,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]
        r = self.client.patch(
            f"/api/v1/items/{created['_id']}/room",
            {"new_room_id": other_room.pk}, format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["itemRoom"], other_room.pk)

    def test_move_item_department(self):
        self._auth_as_admin()
        target_department = Department.objects.create(
            departmentName="Electrical Engineering",
            departmentNameNormalized="electrical engineering",
            createdBy=self.admin,
        )
        target_floor = Floor.objects.create(
            floorName="First", floorNameNormalized="first",
            department=target_department, createdBy=self.admin,
        )
        target_room_type = RoomType.objects.create(
            roomTypeName="Lab", roomTypeNameNormalized="lab",
            department=target_department, createdBy=self.admin,
        )
        target_room = Room.objects.create(
            roomName="E101", roomNameNormalized="e101", floor=target_floor,
            roomType=target_room_type, createdBy=self.admin,
        )
        created = self.client.post("/api/v1/items/", {
            "itemName": "Monitor", "itemCategory": self.category.pk,
            "itemSubCategory": self.sub_category.pk,
            "itemFloor": self.floor.pk, "itemRoom": self.room.pk,
            "itemSource": "Purchase", "itemCost": 100,
            "itemStatus": "Working", "itemAcquiredDate": "2026-01-15",
        }, format="json").data["data"][0]

        r = self.client.patch(
            f"/api/v1/items/{created['_id']}/department",
            {"new_department_id": target_department.pk, "new_room_id": target_room.pk},
            format="json",
        )

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["itemRoom"], target_room.pk)
        self.assertEqual(r.data["data"]["itemFloor"], target_floor.pk)
        self.assertTrue(
            ActivityLog.objects.filter(
                action="Item department updated", entityId=created["_id"]
            ).exists()
        )

    def test_csv_import_preview_and_commit_creates_item_hierarchy(self):
        self._auth_as_admin()
        csv_content = (
            "department,floor,room,room_type,category,subcategory,item_name,model_or_make,source,status,cost,acquired_date,quantity,description\n"
            "Civil Engineering,First Floor,C101,Lab,Electronics,Monitor,Dell Monitor,P2419H,Purchase,Working,25000,2026-01-15,2,For lab\n"
        ).encode()
        preview = self.client.post(
            "/api/v1/items/import/preview",
            {"file": SimpleUploadedFile("items.csv", csv_content, content_type="text/csv")},
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertEqual(preview.data["data"]["validRows"], 1)
        self.assertEqual(preview.data["data"]["totalItems"], 2)

        imported = self.client.post(
            "/api/v1/items/import/commit",
            {"file": SimpleUploadedFile("items.csv", csv_content, content_type="text/csv")},
        )
        self.assertEqual(imported.status_code, status.HTTP_201_CREATED)
        self.assertEqual(imported.data["data"]["importedItems"], 2)
        self.assertEqual(Item.objects.filter(itemName="Dell Monitor").count(), 2)
        self.assertTrue(Department.objects.filter(departmentName="Civil Engineering").exists())
        self.assertTrue(ActivityLog.objects.filter(action="Items imported from CSV").exists())

    def test_csv_import_is_admin_only(self):
        self._auth_as_user()
        csv_content = b"department,floor,room,room_type,item_name,source,status\nCivil,First,C101,Lab,Monitor,Purchase,Working\n"
        response = self.client.post(
            "/api/v1/items/import/preview",
            {"file": SimpleUploadedFile("items.csv", csv_content, content_type="text/csv")},
        )
        assert_legacy_error(response, status.HTTP_403_FORBIDDEN)


class InventoryResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin_password = "admin-pass"
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com",
            password=self.admin_password, phone_number="9800000000",
            role=User.Role.ADMIN, is_staff=True,
        )
        self.user_password = "user-pass"
        self.user = User.objects.create_user(
            username="user", email="user@test.com",
            password=self.user_password, phone_number="9800000001",
            role=User.Role.USER,
        )
        self.admin_client = self.client_class()
        self.admin_client.post("/api/v1/users/login", {
            "username": "admin", "password": self.admin_password,
        }, format="json")
        self.user_client = self.client_class()
        self.user_client.post("/api/v1/users/login", {
            "username": "user", "password": self.user_password,
        }, format="json")

    def test_stats_requires_auth(self):
        r = self.client.get("/api/v1/inventory/stats")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_returns_counts(self):
        r = self.user_client.get("/api/v1/inventory/stats")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("no_total_items", r.data["data"])
        self.assertIn("no_working", r.data["data"])
        self.assertIn("no_repairable", r.data["data"])
        self.assertIn("no_not_working", r.data["data"])
        self.assertIn("inventory_total_value", r.data["data"])

    def test_recent_logs_requires_admin(self):
        r = self.user_client.get("/api/v1/inventory/recent-logs")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_recent_logs_empty_404(self):
        r = self.admin_client.get("/api/v1/inventory/recent-logs")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_recent_logs_nonempty(self):
        ActivityLog.objects.create(action="test", entityType="Item")
        r = self.admin_client.get("/api/v1/inventory/recent-logs")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["data"]), 1)

    def test_recent_logs_respects_admin_enforcement(self):
        r = self.user_client.get("/api/v1/inventory/recent-logs")
        assert_legacy_error(r, status.HTTP_403_FORBIDDEN)
        r2 = self.client.get("/api/v1/inventory/recent-logs")
        self.assertEqual(r2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logs_page_requires_admin(self):
        r = self.user_client.get("/api/v1/inventory/logs/1")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_logs_page_empty(self):
        r = self.admin_client.get("/api/v1/inventory/logs/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalLogs"], 0)
        self.assertEqual(r.data["data"]["logs"], [])

    def test_logs_page_pagination(self):
        for i in range(10):
            ActivityLog.objects.create(action=f"test_{i}", entityType="Item")
        r = self.admin_client.get("/api/v1/inventory/logs/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["totalLogs"], 10)
        self.assertEqual(len(r.data["data"]["logs"]), 6)

    def test_logs_date_filter(self):
        ActivityLog.objects.create(action="old", entityType="Item")
        mid = ActivityLog.objects.create(action="mid", entityType="Item")
        ActivityLog.objects.create(action="new", entityType="Item")
        params = f"0/{mid.created_at.date()}"
        r = self.admin_client.get(f"/api/v1/inventory/logs/1/{params}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreater(r.data["data"]["totalLogs"], 0)

    def test_log_serializer_exposes_id(self):
        log = ActivityLog.objects.create(action="test", entityType="Item")
        r = self.admin_client.get("/api/v1/inventory/logs/1")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["logs"][0]["_id"], log.pk)

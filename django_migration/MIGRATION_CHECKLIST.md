# Resource Conversion Checklist

Work through exactly one resource at a time. Do not mark the next resource as
in progress until the current one has passed its tests and been committed.

## Users — complete

- [x] Model matches original schema: fields, types, relationships, defaults, and validators.
- [x] Serializer validation matches original required fields and custom checks.
- [x] Endpoints match the original URL shapes, methods, and success status codes.
- [x] Authentication and Admin permissions match the original middleware behaviour.
- [x] Tests cover every original User route plus the established refresh endpoint.
- [x] Original validation, duplicate, authorization, invalid-ID, empty-list, and soft-delete edges are tested.
- [x] Tests passing and committed.

## Floors — complete

- [x] Model matches original schema: fields, types, relationships, defaults, and validators.
- [x] Serializer validation matches original required fields and custom checks.
- [x] Endpoints match the original URL shapes, methods, and success status codes.
- [x] Auth/permissions match original middleware behaviour.
- [x] Tests cover CRUD, auth, duplicate, invalid-ID, empty-list, and soft-delete edges (17 tests).
- [x] Tests passing and committed.

## Room types — complete

- [x] Model matches original schema: fields, types, relationships, defaults, and validators.
- [x] Serializer validation matches original required fields and custom checks.
- [x] Endpoints match the original URL shapes, methods, and success status codes.
- [x] Auth/permissions match original middleware behaviour.
- [x] Tests cover CRUD, auth, duplicate, invalid-ID, empty-list, soft-delete, and blank-name edges (18 tests).
- [x] Tests passing and committed.

## Categories — complete

- [x] Model matches original schema: fields, types, relationships, defaults, and validators.
- [x] Serializer validation matches original required fields and custom checks.
- [x] Endpoints match the original URL shapes, methods, and success status codes.
- [x] Auth/permissions match original middleware behaviour.
- [x] Tests cover CRUD, auth, duplicate, invalid-ID, empty-list, blank-name, and description edges (20 tests).
- [x] Tests passing and committed.

## SubCategories — complete

- [x] Model matches original schema: fields, types, relationships, defaults, and validators.
- [x] Serializer validation matches original required fields and custom checks.
- [x] Endpoints match the original URL shapes, methods, and success status codes.
- [x] Auth/permissions match original middleware behaviour.
- [x] Tests cover CRUD, auth, duplicate name/abbr, category-not-found, invalid-ID, soft-delete, and description edges (15 tests).
- [x] Tests passing and committed.

## Rooms — complete

- [x] Model matches original schema: fields, types, relationships, defaults, and validators.
- [x] Serializer validation matches original required fields and custom checks.
- [x] Endpoints match the original URL shapes, methods, and success status codes.
- [x] Auth/permissions match original middleware behaviour.
- [x] Tests cover CRUD, auth, duplicate, invalid-ID, floor-filter, search, and empty-list edges (20 tests).
- [x] Tests passing and committed.

## Items — complete

- [x] Model matches original schema: fields, types, relationships, defaults, and validators.
- [x] Serializer validation matches original required fields and custom checks.
- [x] Endpoints match the original URL shapes, methods, and success status codes.
- [x] Auth/permissions match original middleware behaviour.
- [x] Tests cover CRUD, auth, search, filter, pagination, similar/stats, status/source enums, bulk ops, soft-delete, and history edges (14 tests).
- [x] Tests passing and committed.

## Activity logs / inventory reporting — complete

- [x] ActivityLog model matches original schema.
- [x] Inventory endpoints match original URL shapes, methods, and success status codes.
- [x] Auth/permissions match original middleware behaviour.
- [x] Tests cover stats, recent-logs (empty + populated), logs pagination, date filter, and admin enforcement (10 tests).
- [x] Tests passing.

- [ ] **Activity log writes are not yet integrated into the other views** — logging calls must still be added to individual create/update/delete views.

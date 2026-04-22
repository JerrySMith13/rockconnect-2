# RockConnect API Reference

Base URL: `/api/`

All responses are JSON. Authenticated endpoints require a valid session cookie (Django session auth).

| Section | Endpoints | Documentation |
|---|---|---|
| Users | `/api/users/` | This document |
| Conversations | `/api/conversations/` | [conversations.md](conversations.md) |
| Groups | `/api/groups/` | [groups.md](groups.md) |

---

## Users

### Get Current User

```
GET /api/users/me/
```

**Auth:** Required

Returns the authenticated user's full profile, including private fields.

**Response `200`:**

```json
{
  "id": 1,
  "username": "alice",
  "first_name": "Alice",
  "last_name": "Smith",
  "avatar_url": "https://example.com/avatar.jpg",
  "profile_photo_url": "https://example.com/photo.jpg",
  "bio": "Guitarist and rock collector.",
  "company": "Acme Corp",
  "date_joined": "2026-01-15T08:30:00+00:00",
  "last_login": "2026-04-10T12:00:00+00:00",
  "email": "alice@example.com",
  "is_staff": false
}
```

**Response `403`:** Not authenticated.

---

### Update Current User

```
PATCH /api/users/me/
```

**Auth:** Required

**Content-Type:** `application/json`

**Updatable fields:** `first_name`, `last_name`, `avatar_url`, `profile_photo_url`, `bio`, `company`

**Request body:**

```json
{
  "first_name": "Alice",
  "bio": "Lead guitarist at weekend jams.",
  "company": "Acme Corp"
}
```

**Response `200`:** Returns the full updated user object (same shape as GET).

**Response `400`:**

```json
{
  "error": "Cannot update fields: email, username"
}
```

```json
{
  "error": "Invalid JSON"
}
```

---

### Get User by Username

```
GET /api/users/<username>/
```

**Auth:** Optional

Returns a user's public profile. Private fields (`email`, `is_staff`) are only included when the authenticated user is viewing their own profile.

**Response `200` (public):**

```json
{
  "id": 2,
  "username": "bob",
  "first_name": "Bob",
  "last_name": "",
  "avatar_url": "",
  "profile_photo_url": "",
  "bio": "",
  "company": "",
  "date_joined": "2026-03-01T10:00:00+00:00",
  "last_login": null
}
```

**Response `200` (own profile):** Same as above, plus `email` and `is_staff`.

**Response `404`:** User not found.

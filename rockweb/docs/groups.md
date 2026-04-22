# Groups API Reference

Base URL: `/api/groups/`

All endpoints require a valid session cookie (login required). Unauthenticated requests receive a `302` redirect to the login page. All request bodies must be `application/json`.

---

## Groups

### List Groups

```
GET /api/groups/
```

**Auth:** Required

Returns all groups visible to the authenticated user: all public groups plus any private groups the user belongs to. Ordered alphabetically by name.

**Response `200`:**

```json
[
  {
    "id": 1,
    "name": "Weekend Jammers",
    "slug": "weekend-jammers",
    "bio": "A group for weekend jam sessions.",
    "thumbnail_url": "https://cdn.example.com/groups/jammers.jpg",
    "visibility": "public",
    "post_permission": "anyone",
    "created_at": "2026-04-01T09:00:00+00:00",
    "updated_at": "2026-04-11T14:30:00+00:00",
    "member_count": 12,
    "members": [
      {"id": 1, "username": "alice", "role": "admin", "nickname": "Al"},
      {"id": 2, "username": "bob", "role": "member", "nickname": ""}
    ],
    "your_role": "admin"
  }
]
```

`your_role` is `"admin"`, `"member"`, or `null` if the user is not a member of the group.

---

### Create Group

```
POST /api/groups/
```

**Auth:** Required (**site admin** only)

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Yes | Unique group name. |
| `slug` | `string` | Yes | Unique URL slug. |
| `bio` | `string` | No | Group description. |
| `thumbnail_url` | `string` | No | URL to the group thumbnail image. |
| `visibility` | `string` | No | `"public"` (default) or `"private"`. |
| `post_permission` | `string` | No | `"anyone"` (default) or `"admins"`. |

**Request example:**

```json
{
  "name": "Weekend Jammers",
  "slug": "weekend-jammers",
  "bio": "A group for weekend jam sessions.",
  "thumbnail_url": "https://cdn.example.com/groups/jammers.jpg",
  "visibility": "public",
  "post_permission": "anyone"
}
```

**Response `201`:** Returns the full group object (same shape as list items). The creator is automatically added as a group admin.

**Response `400`:**

```json
{"error": "name and slug are required"}
```

**Response `403`:**

```json
{"error": "Only site admins can create groups"}
```

**Response `409`:**

```json
{"error": "A group with this slug already exists"}
```

```json
{"error": "A group with this name already exists"}
```

---

### Get Group

```
GET /api/groups/<slug>/
```

**Auth:** Required (private groups require membership)

**Response `200`:** Full group object (same shape as list items).

**Response `404`:** Group not found, or private group and user is not a member.

---

### Update Group

```
PATCH /api/groups/<slug>/
```

**Auth:** Required (**group admin** only)

**Updatable fields:** `name`, `bio`, `thumbnail_url`, `visibility`, `post_permission`

**Request body:**

```json
{
  "bio": "Updated description.",
  "post_permission": "admins"
}
```

**Response `200`:** Returns the updated group object.

**Response `400`:**

```json
{"error": "Cannot update fields: slug"}
```

```json
{"error": "name cannot be empty"}
```

**Response `403`:**

```json
{"error": "Group admin role required"}
```

**Response `409`:**

```json
{"error": "A group with this name already exists"}
```

---

### Delete Group

```
DELETE /api/groups/<slug>/
```

**Auth:** Required (**site admin** only)

**Response `200`:**

```json
{"ok": true}
```

**Response `403`:**

```json
{"error": "Only site admins can delete groups"}
```

---

## Members

### List Members

```
GET /api/groups/<slug>/members/
```

**Auth:** Required (private groups require membership)

**Response `200`:**

```json
[
  {
    "id": 1,
    "username": "alice",
    "role": "admin",
    "nickname": "Al",
    "joined_at": "2026-04-01T09:00:00+00:00"
  },
  {
    "id": 2,
    "username": "bob",
    "role": "member",
    "nickname": "",
    "joined_at": "2026-04-05T12:00:00+00:00"
  }
]
```

---

### Join / Add Member

```
POST /api/groups/<slug>/members/
```

**Auth:** Required

Behavior depends on context:

| Scenario | Auth required | Description |
|---|---|---|
| Self-join a public group | Any user | Omit `user_id` or pass your own ID. |
| Self-join a private group | — | Returns `403`. Private groups require an admin to add you. |
| Add another user | **Group admin** | Pass the target `user_id`. Works for both public and private groups. |

**Request body (self-join):**

```json
{}
```

**Request body (admin adding a user):**

```json
{"user_id": 3}
```

**Response `201`:** Returns the updated group object.

**Response `403`:**

```json
{"error": "This is a private group"}
```

```json
{"error": "Group admin role required"}
```

**Response `409`:**

```json
{"error": "Already a member"}
```

```json
{"error": "User is already a member"}
```

---

### Remove Member

```
DELETE /api/groups/<slug>/members/
```

**Auth:** Required (self-remove, or **group admin** to remove others)

**Request body:**

```json
{"user_id": 3}
```

**Response `200`:** Returns the updated group object.

**Response `400`:**

```json
{"error": "user_id is required"}
```

**Response `403`:**

```json
{"error": "Group admin role required"}
```

---

### Update Member Settings

```
PATCH /api/groups/<slug>/members/settings/
```

**Auth:** Required (must be a member)

Updates the authenticated user's own group-specific settings.

**Updatable fields:** `nickname`

**Request body:**

```json
{"nickname": "Al"}
```

**Response `200`:**

```json
{"nickname": "Al"}
```

**Response `400`:**

```json
{"error": "Cannot update fields: role"}
```

**Response `403`:**

```json
{"error": "Not a member of this group"}
```

---

### Update Member Role

```
PATCH /api/groups/<slug>/members/role/
```

**Auth:** Required (**group admin** only)

Promote or demote a group member.

**Request body:**

```json
{"user_id": 3, "role": "admin"}
```

**Valid roles:** `"member"`, `"admin"`

**Response `200`:** Returns the updated group object.

**Response `400`:**

```json
{"error": "user_id and role are required"}
```

```json
{"error": "Invalid role. Must be one of: admin, member"}
```

**Response `403`:**

```json
{"error": "Group admin role required"}
```

**Response `404`:** Target user is not a member of this group.

---

## Member Roles

| Role | Permissions |
|---|---|
| `admin` | Update group settings, add/remove members, promote/demote roles, create/edit/delete any post, pin posts. Assigned to the group creator and can be granted via the role endpoint. |
| `member` | View group, create posts (if `post_permission` allows), edit/delete own posts. |

Group creation and deletion are restricted to **site admins** (`is_staff`), not group admins.

---

## Access Control

| Setting | Values | Effect |
|---|---|---|
| `visibility` | `"public"` / `"private"` | Public groups are discoverable and joinable by any user. Private groups are only visible to members; joining requires an admin to add you. |
| `post_permission` | `"anyone"` / `"admins"` | `"anyone"` lets all members create posts. `"admins"` restricts posting to group admins only. |

---

## Posts

### List Posts

```
GET /api/groups/<slug>/posts/
```

**Auth:** Required (private groups require membership)

Returns posts ordered by pinned status (pinned first) then newest first. Supports page-based pagination.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `int` | `1` | Page number (1-indexed). |
| `limit` | `int` | `20` | Posts per page. Maximum `50`. |

**Response `200`:**

```json
{
  "posts": [
    {
      "id": 1,
      "group_id": 1,
      "author": {"id": 1, "username": "alice"},
      "title": "Welcome to the group!",
      "body": "Say hello and introduce yourself.",
      "created_at": "2026-04-01T09:00:00+00:00",
      "edited_at": null,
      "pinned": true
    },
    {
      "id": 5,
      "group_id": 1,
      "author": {"id": 2, "username": "bob"},
      "title": "Saturday jam recap",
      "body": "Great session everyone! Here are some notes...",
      "created_at": "2026-04-10T18:00:00+00:00",
      "edited_at": "2026-04-10T19:30:00+00:00",
      "pinned": false
    }
  ],
  "total": 12,
  "page": 1,
  "limit": 20
}
```

`author` is `null` when the original author's account has been deleted.

---

### Create Post

```
POST /api/groups/<slug>/posts/
```

**Auth:** Required (must be a member; if `post_permission` is `"admins"`, **group admin** only)

**Request body:**

```json
{
  "title": "Saturday jam recap",
  "body": "Great session everyone!"
}
```

**Response `201`:** Returns the full post object.

**Response `400`:**

```json
{"error": "Post title is required"}
```

```json
{"error": "Post body is required"}
```

**Response `403`:**

```json
{"error": "Not a member of this group"}
```

```json
{"error": "Only group admins are allowed to post in this group"}
```

---

### Get Post

```
GET /api/groups/<slug>/posts/<id>/
```

**Auth:** Required (private groups require membership)

**Response `200`:** Full post object (same shape as list items).

**Response `404`:** Post not found or does not belong to this group.

---

### Edit Post

```
PATCH /api/groups/<slug>/posts/<id>/
```

**Auth:** Required (post author or **group admin**)

**Updatable fields:** `title`, `body`, `pinned` (admin only)

**Request body:**

```json
{"body": "Updated content.", "pinned": true}
```

**Response `200`:** Returns the updated post object. The `edited_at` field is set to the current timestamp.

**Response `400`:**

```json
{"error": "Post title is required"}
```

```json
{"error": "Cannot update fields: author"}
```

**Response `403`:**

```json
{"error": "You can only edit your own posts"}
```

```json
{"error": "Only group admins can pin posts"}
```

---

### Delete Post

```
DELETE /api/groups/<slug>/posts/<id>/
```

**Auth:** Required (post author or **group admin**)

**Response `200`:**

```json
{"ok": true}
```

**Response `403`:**

```json
{"error": "You can only delete your own posts"}
```

---

## Group Requests

Group requests allow any authenticated user to propose a new group. Requests are reviewed by site admins.

### List Group Requests

```
GET /api/groups/requests/
```

**Auth:** Required

Regular users see only their own requests. Site admins see all requests.

**Response `200`:**

```json
[
  {
    "id": 1,
    "group_name": "Blues Enthusiasts",
    "contact_email": "alice@example.com",
    "comments": "We'd like a space to discuss blues guitar techniques.",
    "status": "pending",
    "created_at": "2026-04-10T08:00:00+00:00",
    "requester": "alice"
  }
]
```

---

### Submit Group Request

```
POST /api/groups/requests/
```

**Auth:** Required

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `group_name` | `string` | Yes | Proposed group name. |
| `contact_email` | `string` | Yes | Contact email for follow-up. |
| `comments` | `string` | No | Additional context or justification. |

**Request example:**

```json
{
  "group_name": "Blues Enthusiasts",
  "contact_email": "alice@example.com",
  "comments": "We'd like a space to discuss blues guitar techniques."
}
```

**Response `201`:**

```json
{
  "id": 1,
  "group_name": "Blues Enthusiasts",
  "contact_email": "alice@example.com",
  "comments": "We'd like a space to discuss blues guitar techniques.",
  "status": "pending",
  "created_at": "2026-04-10T08:00:00+00:00"
}
```

**Response `400`:**

```json
{"error": "group_name is required"}
```

```json
{"error": "contact_email is required"}
```

---

### Review Group Request

```
PATCH /api/groups/requests/<id>/review/
```

**Auth:** Required (**site admin** only)

**Request body:**

```json
{"status": "approved"}
```

**Valid values for `status`:** `"approved"`, `"rejected"`

**Response `200`:**

```json
{
  "id": 1,
  "group_name": "Blues Enthusiasts",
  "status": "approved",
  "reviewed_at": "2026-04-11T15:00:00+00:00",
  "reviewed_by": "admin_user"
}
```

**Response `400`:**

```json
{"error": "status must be one of: approved, rejected"}
```

**Response `403`:**

```json
{"error": "Only site admins can review group requests"}
```

---

## Common Error Responses

These errors can occur on any endpoint:

| Status | Meaning |
|---|---|
| `302` | Not authenticated — redirects to login page. |
| `400` | Invalid JSON body or missing/invalid fields. |
| `403` | Authenticated but not authorized (not a member, insufficient role). |
| `404` | Group or post not found (also returned for private groups the user cannot access). |
| `405` | HTTP method not allowed on this endpoint. |
| `409` | Conflict — duplicate name, slug, or membership. |

# Conversations API Reference

Base URL: `/api/conversations/`

All endpoints require a valid session cookie (login required). Unauthenticated requests receive a `302` redirect to the login page. All request bodies must be `application/json`.

---

## Conversations

### List Conversations

```
GET /api/conversations/
```

**Auth:** Required

Returns all conversations the authenticated user belongs to, ordered by most recent activity.

**Response `200`:**

```json
[
  {
    "id": 1,
    "title": "Project Chat",
    "is_group": true,
    "created_at": "2026-04-01T09:00:00+00:00",
    "updated_at": "2026-04-11T14:30:00+00:00",
    "members": [
      {"id": 1, "username": "alice", "role": "owner"},
      {"id": 2, "username": "bob", "role": "member"},
      {"id": 3, "username": "carol", "role": "admin"}
    ],
    "last_message": {
      "id": 42,
      "body": "See you at the meetup tomorrow!",
      "sender": "bob",
      "created_at": "2026-04-11T14:30:00+00:00"
    },
    "unread_count": 3
  }
]
```

`last_message` is `null` when the conversation has no messages. `last_message.body` is truncated to 100 characters.

`unread_count` is the number of messages from other users received after the authenticated user's last `mark_read` call. If the user has never marked the conversation as read, all messages from others are counted.

---

### Create Conversation

```
POST /api/conversations/
```

**Auth:** Required

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `member_ids` | `int[]` | Yes | User IDs to include. The creator is added automatically. |
| `title` | `string` | No | Conversation title (mainly useful for groups). |
| `is_group` | `boolean` | No | Force group mode. Defaults to `true` when more than 2 members. |

**Request example (direct message):**

```json
{
  "member_ids": [2]
}
```

**Response `201`:** Returns the full conversation object (same shape as list items).

**Duplicate prevention:** For 1-on-1 conversations, if a direct conversation already exists between the two users, the existing conversation is returned with status `200` instead of creating a duplicate.

**Request example (group):**

```json
{
  "member_ids": [2, 3, 4],
  "title": "Weekend Jam Session",
  "is_group": true
}
```

**Response `400`:**

```json
{"error": "A conversation requires at least 2 members"}
```

```json
{"error": "member_ids must be a list"}
```

---

### Get Conversation

```
GET /api/conversations/<id>/
```

**Auth:** Required (must be a member)

**Response `200`:** Full conversation object (same shape as list items).

**Response `403`:**

```json
{"error": "Not a member of this conversation"}
```

**Response `404`:** Conversation not found.

---

### Update Conversation

```
PATCH /api/conversations/<id>/
```

**Auth:** Required (admin or owner, group only)

**Updatable fields:** `title`

**Request body:**

```json
{"title": "New Group Name"}
```

**Response `200`:** Returns the updated conversation object.

**Response `400`:**

```json
{"error": "Cannot rename a direct conversation"}
```

```json
{"error": "Cannot update fields: is_group"}
```

**Response `403`:**

```json
{"error": "Only admins and owners can update the conversation"}
```

---

### Leave Conversation

```
DELETE /api/conversations/<id>/
```

**Auth:** Required (must be a member)

Removes the authenticated user from the conversation. If no members remain after leaving, the conversation and all its messages are deleted.

**Response `200`:**

```json
{"ok": true}
```

---

## Members

### Add Member

```
POST /api/conversations/<id>/members/
```

**Auth:** Required (admin or owner, group only)

**Request body:**

```json
{"user_id": 4}
```

**Response `201`:** Returns the updated conversation object.

**Response `400`:**

```json
{"error": "Cannot add members to a direct conversation"}
```

**Response `403`:**

```json
{"error": "Only admins and owners can add members"}
```

**Response `409`:**

```json
{"error": "User is already a member"}
```

---

### Remove Member

```
DELETE /api/conversations/<id>/members/
```

**Auth:** Required (admin/owner to remove others, any member to remove self)

**Request body:**

```json
{"user_id": 4}
```

**Response `200`:** Returns the updated conversation object. If the removed user was the last member, the conversation is deleted and the response is:

```json
{"ok": true}
```

**Response `403`:**

```json
{"error": "You can only remove yourself or require admin/owner role"}
```

---

## Member Roles

| Role | Permissions |
|---|---|
| `owner` | Full control: rename group, add/remove members, delete any message. Assigned to the conversation creator. |
| `admin` | Same as owner. Can be granted by updating the membership (not yet exposed via API). |
| `member` | Send/edit/delete own messages, leave the conversation. |

---

## Messages

### List Messages

```
GET /api/conversations/<id>/messages/
```

**Auth:** Required (must be a member)

Returns messages in chronological order (oldest first). Supports cursor-based pagination.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `before` | `int` | — | Message ID cursor. Returns messages older than this message. |
| `limit` | `int` | `50` | Number of messages to return. Maximum `100`. |

**Request example:**

```
GET /api/conversations/1/messages/?before=42&limit=20
```

**Response `200`:**

```json
[
  {
    "id": 21,
    "conversation_id": 1,
    "sender": {"id": 2, "username": "bob"},
    "body": "Hey, are we still on for Saturday?",
    "created_at": "2026-04-10T10:00:00+00:00",
    "edited_at": null,
    "is_system": false,
    "attachments": []
  },
  {
    "id": 22,
    "conversation_id": 1,
    "sender": {"id": 1, "username": "alice"},
    "body": "Yes! I'll bring my guitar.",
    "created_at": "2026-04-10T10:05:00+00:00",
    "edited_at": null,
    "is_system": false,
    "attachments": [
      {
        "id": 1,
        "filename": "setlist.pdf",
        "file_url": "https://cdn.example.com/setlist.pdf",
        "content_type": "application/pdf",
        "size_bytes": 48210
      }
    ]
  }
]
```

`sender` is `null` for messages where the original sender's account has been deleted. System-generated messages (e.g., "Alice joined the conversation") have `is_system: true`.

**Response `400`:**

```json
{"error": "Invalid 'before' cursor"}
```

---

### Send Message

```
POST /api/conversations/<id>/messages/
```

**Auth:** Required (must be a member)

**Request body:**

```json
{"body": "Hey everyone!"}
```

**Response `201`:** Returns the full message object.

Sending a message also bumps the conversation's `updated_at` timestamp, which affects sort order in the conversation list.

**Response `400`:**

```json
{"error": "Message body is required"}
```

---

### Get Message

```
GET /api/conversations/<id>/messages/<message_id>/
```

**Auth:** Required (must be a member)

**Response `200`:** Full message object (same shape as list items).

**Response `404`:** Message not found or does not belong to this conversation.

---

### Edit Message

```
PATCH /api/conversations/<id>/messages/<message_id>/
```

**Auth:** Required (message sender only)

**Request body:**

```json
{"body": "Updated message text"}
```

**Response `200`:** Returns the updated message object. The `edited_at` field is set to the current timestamp.

**Response `400`:**

```json
{"error": "Message body is required"}
```

**Response `403`:**

```json
{"error": "You can only edit your own messages"}
```

---

### Delete Message

```
DELETE /api/conversations/<id>/messages/<message_id>/
```

**Auth:** Required (message sender, or conversation admin/owner)

**Response `200`:**

```json
{"ok": true}
```

**Response `403`:**

```json
{"error": "You can only delete your own messages"}
```

---

## Read Receipts

### Mark Conversation as Read

```
POST /api/conversations/<id>/read/
```

**Auth:** Required (must be a member)

Updates the authenticated user's `last_read_at` cursor to the current time. This resets the `unread_count` for the conversation in list responses.

**Request body:** None required.

**Response `200`:**

```json
{
  "ok": true,
  "last_read_at": "2026-04-11T15:00:00+00:00"
}
```

---

## Search

### Search Messages

```
GET /api/conversations/search/?q=<term>
```

**Auth:** Required

Searches message bodies across all conversations the authenticated user belongs to. Returns up to 25 results, ordered by most recent first. Uses case-insensitive substring matching.

**Query parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `q` | `string` | Yes | Search term. |

**Response `200`:**

```json
[
  {
    "id": 42,
    "conversation_id": 1,
    "conversation_title": "Project Chat",
    "sender": "bob",
    "body": "Don't forget the meetup tomorrow!",
    "created_at": "2026-04-11T14:30:00+00:00"
  }
]
```

**Response `400`:**

```json
{"error": "Query parameter 'q' is required"}
```

---

## Common Error Responses

These errors can occur on any endpoint:

| Status | Meaning |
|---|---|
| `302` | Not authenticated — redirects to login page. |
| `400` | Invalid JSON body or missing/invalid fields. |
| `403` | Authenticated but not authorized (not a member, insufficient role). |
| `404` | Conversation or message not found. |
| `405` | HTTP method not allowed on this endpoint. |

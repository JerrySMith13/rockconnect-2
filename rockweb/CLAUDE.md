# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RockConnect is a Django 6.0 web application ("rockweb") for community messaging, groups, and user profiles. Authentication uses django-allauth with Google OAuth support.

## Development Commands

```bash
# Activate virtualenv
source venv/bin/activate

# Run dev server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Run tests
python manage.py test                  # all tests
python manage.py test messages         # single app
python manage.py test messages.tests.TestClassName.test_method  # single test

# Create superuser
python manage.py createsuperuser
```

## Architecture

- **Django project**: `rockweb/` (settings, root URL conf)
- **Apps**: `messages/`, `users/`, `groups/`, `api/`
- **Custom user model**: `users.User` (extends `AbstractUser` with `avatar_url`, `profile_photo_url`, `bio`, `company`) — referenced as `AUTH_USER_MODEL = "users.User"`
- **Auth**: django-allauth handles signup/login/OAuth; allauth URLs mounted at `/accounts/`
- **Database**: PostgreSQL via psycopg, configured through a pg_service entry named `rockweb`
- **Templates**: app-local (e.g. `users/templates/users/`, `messages/templates/messages/`, `groups/templates/groups/`)
- **Static assets**: `static/css/` (global, account, profile, chat, groups styles), `static/js/` (chat.js)
- **Docs**: `docs/` (api.md, conversations.md, groups.md, accounts.md)

## Apps

### `messages/` — Messaging & Conversations
- **Models**: `Conversation` (1-on-1 and group chats), `ConversationMember` (membership with roles: member/admin/owner and read receipts), `Message` (with PostgreSQL full-text search), `MessageAttachment`
- **Views**: `chat_page` (server-rendered SPA shell) plus REST API endpoints for conversations, messages, members, read receipts, and search
- **URLs** (mounted at `/api/conversations/`): CRUD for conversations, members, messages; `mark_read`; `search_messages`

### `users/` — User Accounts & Profiles
- **Models**: `User` (extends `AbstractUser` — `avatar_url`, `profile_photo_url`, `bio`, `company`)
- **Views**: `account` page (edit profile), `profile` page (public view), API endpoints `api_me` (GET/PATCH) and `api_user_detail` (GET)
- **URLs**: `/users/account/`, `/users/profile/<username>/`, API at `/api/users/`

### `groups/` — Community Groups & Posts
- **Models**: `Group` (public/private visibility, post permission settings), `GroupMember` (member/admin roles with optional nickname), `GroupPost` (with full-text search, pinning), `GroupRequest` (pending/approved/rejected for new group creation)
- **Views**: `group_list_page`, `group_detail_page`, `group_admin_page`, `group_request_page` plus REST API endpoints for groups, members, posts, and group requests
- **URLs**: Pages at `/groups/`, API at `/api/groups/`

### `api/` — API URL Router
- Aggregates API URLs from `users`, `messages`, and `groups` apps under `/api/`

## URL Structure

| Path | Target |
|---|---|
| `/chat/` | Messages chat page |
| `/groups/` | Group listing and detail pages |
| `/users/` | User account and profile pages |
| `/api/` | REST API (conversations, groups, users) |
| `/accounts/` | django-allauth auth flows |
| `/admin/` | Django admin |

## Key Configuration

- Settings module: `rockweb.settings`
- Google OAuth client_id/secret are placeholders in settings — must be configured via admin or environment
- `ACCOUNT_LOGIN_METHODS` accepts both email and username
- `django.contrib.postgres` enabled for full-text search (`SearchVectorField` on Message and GroupPost)

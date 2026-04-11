# Accounts

RockConnect uses a custom user model (`users.User`) that extends Django's `AbstractUser`. Authentication is handled by django-allauth, which provides signup, login, logout, and Google OAuth flows.

---

## User Model Fields

| Field | Type | Description |
|---|---|---|
| `username` | CharField | Unique username (inherited from AbstractUser) |
| `email` | EmailField | Email address (inherited) |
| `first_name` | CharField | First name (inherited) |
| `last_name` | CharField | Last name (inherited) |
| `avatar_url` | URLField (max 500) | Avatar URL, typically populated by OAuth providers |
| `profile_photo_url` | URLField (max 500) | User-provided profile photo link |
| `bio` | TextField (max 500) | Short biography |
| `company` | CharField (max 150) | Company or school name |
| `date_joined` | DateTimeField | When the account was created (inherited) |
| `last_login` | DateTimeField | Last login timestamp (inherited) |

### Profile photo precedence

Templates display the first available image in this order:
1. `profile_photo_url` — explicitly set by the user
2. `avatar_url` — auto-populated from OAuth (e.g. Google profile picture)
3. Letter placeholder — first letter of the username

---

## Pages

### Account page — `/users/account/`

**Auth:** Login required.

Displays the current user's profile information and an inline edit form. The form submits via JavaScript to the `PATCH /api/users/me/` endpoint and updates the following fields:

- First name
- Last name
- Profile photo URL
- Bio (max 500 characters)
- Company / School

On success the page reloads to reflect the changes.

### Public profile — `/users/<username>/`

**Auth:** None required.

Displays a user's public profile:

- Profile photo / avatar with gradient ring
- Display name, username, and company/school in the header
- Bio card (shown only when the user has written a bio)
- Profile details grid: email (hidden from other users), join date, company/school, username, last active
- Activity stats: days as member
- If viewing your own profile: links to edit account and log out

---

## Authentication

All auth flows are provided by django-allauth, mounted at `/accounts/`.

| URL | Purpose |
|---|---|
| `/accounts/signup/` | Email/password registration |
| `/accounts/login/` | Login (email or username) |
| `/accounts/logout/` | Logout |
| `/accounts/google/login/` | Google OAuth sign-in |

`ACCOUNT_LOGIN_METHODS` is configured to accept both email and username.

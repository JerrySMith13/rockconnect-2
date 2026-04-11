# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RockConnect is a Django 6.0 web application ("rockweb") with messaging and user account features. Authentication uses django-allauth with Google OAuth support.

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
- **Apps**: `messages/` (messaging), `users/` (accounts)
- **Custom user model**: `users.User` (extends `AbstractUser` with `avatar_url`) — referenced as `AUTH_USER_MODEL = "users.User"`
- **Auth**: django-allauth handles signup/login/OAuth; allauth URLs mounted at `/accounts/`
- **Database**: PostgreSQL via psycopg, configured through a pg_service entry named `rockweb`
- **Templates**: app-local (`users/templates/users/`)

## Key Configuration

- Settings module: `rockweb.settings`
- Google OAuth client_id/secret are placeholders in settings — must be configured via admin or environment
- `ACCOUNT_LOGIN_METHODS` accepts both email and username

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

User = get_user_model()


@login_required
def account(request):
    return render(request, "users/account.html")


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    days_since_joined = (timezone.now() - profile_user.date_joined).days

    return render(request, "users/profile.html", {
        "profile_user": profile_user,
        "is_own_profile": is_own_profile,
        "days_since_joined": days_since_joined,
    })


# ── REST API ─────────────────────────────────────────────────

def _user_to_dict(user, include_private=False):
    """Serialize a user to a dict. Private fields only for the user themselves."""
    data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": user.avatar_url,
        "profile_photo_url": user.profile_photo_url,
        "bio": user.bio,
        "company": user.company,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
    if include_private:
        data["email"] = user.email
        data["is_staff"] = user.is_staff
    return data


@login_required
@require_http_methods(["GET", "PATCH"])
def api_me(request):
    """GET current user or PATCH to update mutable fields."""
    if request.method == "GET":
        return JsonResponse(_user_to_dict(request.user, include_private=True))

    # PATCH
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    allowed_fields = {"first_name", "last_name", "avatar_url", "profile_photo_url", "bio", "company"}
    unknown = set(body.keys()) - allowed_fields
    if unknown:
        return JsonResponse(
            {"error": f"Cannot update fields: {', '.join(sorted(unknown))}"},
            status=400,
        )

    for field, value in body.items():
        setattr(request.user, field, value)
    request.user.save(update_fields=list(body.keys()))

    return JsonResponse(_user_to_dict(request.user, include_private=True))


@require_http_methods(["GET"])
def api_user_detail(request, username):
    """Public read-only profile for any user."""
    user = get_object_or_404(User, username=username)
    include_private = request.user.is_authenticated and request.user == user
    return JsonResponse(_user_to_dict(user, include_private=include_private))

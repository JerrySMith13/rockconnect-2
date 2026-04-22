import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Group, GroupMember, GroupPost, GroupRequest

User = get_user_model()


# ── Page views ───────────────────────────────────────────────

def group_list_page(request):
    """Public page listing all visible groups."""
    public = Group.objects.filter(visibility=Group.Visibility.PUBLIC)
    if request.user.is_authenticated:
        private_mine = Group.objects.filter(
            visibility=Group.Visibility.PRIVATE,
            memberships__user=request.user,
        )
        groups = (public | private_mine).distinct()
    else:
        groups = public

    groups = groups.annotate(member_count=Count("memberships")).order_by("name")
    return render(request, "groups/group_list.html", {"groups": groups})


def group_detail_page(request, group_slug):
    """Blog-style group page showing thumbnail, bio, and posts."""
    group = get_object_or_404(Group, slug=group_slug)

    # Private group visibility check
    is_member = False
    is_admin = False
    if request.user.is_authenticated:
        membership = group.memberships.filter(user=request.user).first()
        if membership:
            is_member = True
            is_admin = membership.role == GroupMember.Role.ADMIN

    if group.visibility == Group.Visibility.PRIVATE and not is_member:
        return render(request, "groups/group_list.html", {
            "groups": Group.objects.none(),
        })

    member_count = group.memberships.count()
    can_post = is_member and (
        group.post_permission == Group.PostPermission.ANYONE or is_admin
    )
    return render(request, "groups/group_detail.html", {
        "group": group,
        "is_member": is_member,
        "is_admin": is_admin,
        "can_post": can_post,
        "member_count": member_count,
    })


@login_required
def group_admin_page(request, group_slug):
    """Admin panel for group admins to manage settings, members, posts."""
    group = get_object_or_404(Group, slug=group_slug)
    membership = group.memberships.filter(user=request.user).first()
    if not membership or membership.role != GroupMember.Role.ADMIN:
        return HttpResponseForbidden("Group admin access required.")

    members = list(group.memberships.select_related("user").values(
        "user__id", "user__username", "role", "nickname",
    ))
    member_count = len(members)
    return render(request, "groups/group_admin.html", {
        "group": group,
        "members": members,
        "member_count": member_count,
    })


@login_required
def group_request_page(request):
    """Page for users to submit and view their group requests."""
    user_requests = GroupRequest.objects.filter(requester=request.user)
    return render(request, "groups/group_request.html", {
        "requests": user_requests,
    })


# ── Helpers ──────────────────────────────────────────────────

def _parse_json(request):
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


def _group_to_dict(group, user=None):
    members = list(
        group.memberships.select_related("user").values_list(
            "user__id", "user__username", "role", "nickname",
        )
    )
    membership = None
    if user and user.is_authenticated:
        membership = next((m for m in members if m[0] == user.id), None)

    return {
        "id": group.id,
        "name": group.name,
        "slug": group.slug,
        "bio": group.bio,
        "thumbnail_url": group.thumbnail_url,
        "visibility": group.visibility,
        "post_permission": group.post_permission,
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
        "member_count": len(members),
        "members": [
            {"id": uid, "username": uname, "role": role, "nickname": nick}
            for uid, uname, role, nick in members
        ],
        "your_role": membership[2] if membership else None,
    }


def _post_to_dict(post):
    return {
        "id": post.id,
        "group_id": post.group_id,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
        } if post.author else None,
        "title": post.title,
        "body": post.body,
        "created_at": post.created_at.isoformat(),
        "edited_at": post.edited_at.isoformat() if post.edited_at else None,
        "pinned": post.pinned,
    }


def _require_membership(user, group):
    """Return (membership, None) or (None, 403 response)."""
    try:
        return group.memberships.get(user=user), None
    except GroupMember.DoesNotExist:
        return None, JsonResponse({"error": "Not a member of this group"}, status=403)


def _require_group_admin(membership):
    """Return None if admin, or a 403 response."""
    if membership.role != GroupMember.Role.ADMIN:
        return JsonResponse({"error": "Group admin role required"}, status=403)
    return None


def _can_view_group(user, group):
    """Public groups are visible to all; private groups require membership."""
    if group.visibility == Group.Visibility.PUBLIC:
        return True
    return group.memberships.filter(user=user).exists()


# ── Groups ───────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def group_list(request):
    """
    GET  — list groups visible to the user (public + user's private groups).
    POST — create a group (site admin only).
    """
    if request.method == "GET":
        public = Group.objects.filter(visibility=Group.Visibility.PUBLIC)
        private_mine = Group.objects.filter(
            visibility=Group.Visibility.PRIVATE,
            memberships__user=request.user,
        )
        groups = (public | private_mine).distinct().order_by("name")
        return JsonResponse(
            [_group_to_dict(g, request.user) for g in groups],
            safe=False,
        )

    # POST — site admin only
    if not request.user.is_staff:
        return JsonResponse({"error": "Only site admins can create groups"}, status=403)

    body, err = _parse_json(request)
    if err:
        return err

    name = body.get("name", "").strip()
    slug = body.get("slug", "").strip()
    if not name or not slug:
        return JsonResponse({"error": "name and slug are required"}, status=400)

    if Group.objects.filter(slug=slug).exists():
        return JsonResponse({"error": "A group with this slug already exists"}, status=409)
    if Group.objects.filter(name=name).exists():
        return JsonResponse({"error": "A group with this name already exists"}, status=409)

    group = Group.objects.create(
        name=name,
        slug=slug,
        bio=body.get("bio", ""),
        thumbnail_url=body.get("thumbnail_url", ""),
        visibility=body.get("visibility", Group.Visibility.PUBLIC),
        post_permission=body.get("post_permission", Group.PostPermission.ANYONE),
    )
    # Creator becomes group admin
    GroupMember.objects.create(
        group=group, user=request.user, role=GroupMember.Role.ADMIN,
    )

    return JsonResponse(_group_to_dict(group, request.user), status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def group_detail(request, group_slug):
    """
    GET    — group detail.
    PATCH  — update group settings (group admin only).
    DELETE — delete group (site admin only).
    """
    group = get_object_or_404(Group, slug=group_slug)

    if request.method == "GET":
        if not _can_view_group(request.user, group):
            return JsonResponse({"error": "Group not found"}, status=404)
        return JsonResponse(_group_to_dict(group, request.user))

    # PATCH — group admin
    if request.method == "PATCH":
        membership, err = _require_membership(request.user, group)
        if err:
            return err
        err = _require_group_admin(membership)
        if err:
            return err

        body, err = _parse_json(request)
        if err:
            return err

        allowed = {"name", "bio", "thumbnail_url", "visibility", "post_permission"}
        unknown = set(body.keys()) - allowed
        if unknown:
            return JsonResponse(
                {"error": f"Cannot update fields: {', '.join(sorted(unknown))}"},
                status=400,
            )

        if "name" in body:
            new_name = body["name"].strip()
            if not new_name:
                return JsonResponse({"error": "name cannot be empty"}, status=400)
            if Group.objects.filter(name=new_name).exclude(id=group.id).exists():
                return JsonResponse({"error": "A group with this name already exists"}, status=409)
            group.name = new_name

        for field in ("bio", "thumbnail_url", "visibility", "post_permission"):
            if field in body:
                setattr(group, field, body[field])

        group.save(update_fields=[f for f in allowed if f in body] + ["updated_at"])
        return JsonResponse(_group_to_dict(group, request.user))

    # DELETE — site admin only
    if not request.user.is_staff:
        return JsonResponse({"error": "Only site admins can delete groups"}, status=403)
    group.delete()
    return JsonResponse({"ok": True})


# ── Members ──────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def group_members(request, group_slug):
    """
    GET    — list members.
    POST   — add member / join (public groups: self-join; private: admin-only).
    DELETE — remove member (admin, or self to leave).
    """
    group = get_object_or_404(Group, slug=group_slug)

    if request.method == "GET":
        if not _can_view_group(request.user, group):
            return JsonResponse({"error": "Group not found"}, status=404)
        members = group.memberships.select_related("user").values_list(
            "user__id", "user__username", "role", "nickname", "joined_at",
        )
        return JsonResponse([
            {
                "id": uid, "username": uname, "role": role,
                "nickname": nick, "joined_at": joined.isoformat(),
            }
            for uid, uname, role, nick, joined in members
        ], safe=False)

    body, err = _parse_json(request)
    if err:
        return err

    if request.method == "POST":
        user_id = body.get("user_id")
        # Self-join (no user_id or user_id == self)
        if not user_id or user_id == request.user.id:
            if group.visibility == Group.Visibility.PRIVATE:
                # Must be admin to add to private group
                membership, merr = _require_membership(request.user, group)
                if merr:
                    return JsonResponse({"error": "This is a private group"}, status=403)
            _, created = GroupMember.objects.get_or_create(
                group=group, user=request.user,
            )
            if not created:
                return JsonResponse({"error": "Already a member"}, status=409)
            return JsonResponse(_group_to_dict(group, request.user), status=201)

        # Adding another user — requires group admin
        membership, err = _require_membership(request.user, group)
        if err:
            return err
        aerr = _require_group_admin(membership)
        if aerr:
            return aerr
        target_user = get_object_or_404(User, id=user_id)
        _, created = GroupMember.objects.get_or_create(
            group=group, user=target_user,
        )
        if not created:
            return JsonResponse({"error": "User is already a member"}, status=409)
        return JsonResponse(_group_to_dict(group, request.user), status=201)

    # DELETE — remove member
    user_id = body.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id is required"}, status=400)

    target_user = get_object_or_404(User, id=user_id)
    is_self = target_user == request.user

    if not is_self:
        membership, err = _require_membership(request.user, group)
        if err:
            return err
        aerr = _require_group_admin(membership)
        if aerr:
            return aerr

    GroupMember.objects.filter(group=group, user=target_user).delete()
    return JsonResponse(_group_to_dict(group, request.user))


# ── Member settings (nickname, etc.) ─────────────────────────

@login_required
@require_http_methods(["PATCH"])
def member_settings(request, group_slug):
    """PATCH — update your own group-specific settings (nickname, etc.)."""
    group = get_object_or_404(Group, slug=group_slug)
    membership, err = _require_membership(request.user, group)
    if err:
        return err

    body, err = _parse_json(request)
    if err:
        return err

    allowed = {"nickname"}
    unknown = set(body.keys()) - allowed
    if unknown:
        return JsonResponse(
            {"error": f"Cannot update fields: {', '.join(sorted(unknown))}"},
            status=400,
        )

    if "nickname" in body:
        membership.nickname = body["nickname"]

    membership.save(update_fields=[f for f in allowed if f in body])
    return JsonResponse({
        "nickname": membership.nickname,
    })


# ── Member role management ───────────────────────────────────

@login_required
@require_http_methods(["PATCH"])
def member_role(request, group_slug):
    """PATCH — promote/demote a member (group admin only). Body: {user_id, role}."""
    group = get_object_or_404(Group, slug=group_slug)
    my_membership, err = _require_membership(request.user, group)
    if err:
        return err
    aerr = _require_group_admin(my_membership)
    if aerr:
        return aerr

    body, err = _parse_json(request)
    if err:
        return err

    user_id = body.get("user_id")
    new_role = body.get("role")
    if not user_id or not new_role:
        return JsonResponse({"error": "user_id and role are required"}, status=400)

    valid_roles = {r.value for r in GroupMember.Role}
    if new_role not in valid_roles:
        return JsonResponse({"error": f"Invalid role. Must be one of: {', '.join(sorted(valid_roles))}"}, status=400)

    target = get_object_or_404(GroupMember, group=group, user_id=user_id)
    target.role = new_role
    target.save(update_fields=["role"])
    return JsonResponse(_group_to_dict(group, request.user))


# ── Posts ─────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def post_list(request, group_slug):
    """
    GET  — list posts (paginated: ?page=1&limit=20).
    POST — create a post (permission-checked).
    """
    group = get_object_or_404(Group, slug=group_slug)

    if not _can_view_group(request.user, group):
        return JsonResponse({"error": "Group not found"}, status=404)

    if request.method == "GET":
        page = max(int(request.GET.get("page", 1)), 1)
        limit = min(int(request.GET.get("limit", 20)), 50)
        offset = (page - 1) * limit

        qs = group.posts.select_related("author")
        total = qs.count()
        posts = list(qs[offset:offset + limit])

        return JsonResponse({
            "posts": [_post_to_dict(p) for p in posts],
            "total": total,
            "page": page,
            "limit": limit,
        })

    # POST — create
    membership, err = _require_membership(request.user, group)
    if err:
        return err

    if group.post_permission == Group.PostPermission.ADMINS:
        aerr = _require_group_admin(membership)
        if aerr:
            return JsonResponse(
                {"error": "Only group admins are allowed to post in this group"},
                status=403,
            )

    body, err = _parse_json(request)
    if err:
        return err

    title = body.get("title", "").strip()
    text = body.get("body", "").strip()
    if not title:
        return JsonResponse({"error": "Post title is required"}, status=400)
    if not text:
        return JsonResponse({"error": "Post body is required"}, status=400)

    post = GroupPost.objects.create(
        group=group,
        author=request.user,
        title=title,
        body=text,
    )
    return JsonResponse(_post_to_dict(post), status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def post_detail(request, group_slug, post_id):
    """
    GET    — single post.
    PATCH  — edit post (author or group admin).
    DELETE — delete post (author or group admin).
    """
    group = get_object_or_404(Group, slug=group_slug)

    if not _can_view_group(request.user, group):
        return JsonResponse({"error": "Group not found"}, status=404)

    post = get_object_or_404(
        GroupPost.objects.select_related("author"),
        id=post_id,
        group=group,
    )

    if request.method == "GET":
        return JsonResponse(_post_to_dict(post))

    # Write operations require membership
    membership, err = _require_membership(request.user, group)
    if err:
        return err

    is_author = post.author == request.user
    is_admin = membership.role == GroupMember.Role.ADMIN

    if request.method == "PATCH":
        if not is_author and not is_admin:
            return JsonResponse({"error": "You can only edit your own posts"}, status=403)

        body, err = _parse_json(request)
        if err:
            return err

        allowed = {"title", "body", "pinned"}
        # Only admins can pin/unpin
        if "pinned" in body and not is_admin:
            return JsonResponse({"error": "Only group admins can pin posts"}, status=403)

        unknown = set(body.keys()) - allowed
        if unknown:
            return JsonResponse(
                {"error": f"Cannot update fields: {', '.join(sorted(unknown))}"},
                status=400,
            )

        if "title" in body:
            val = body["title"].strip()
            if not val:
                return JsonResponse({"error": "Post title is required"}, status=400)
            post.title = val
        if "body" in body:
            val = body["body"].strip()
            if not val:
                return JsonResponse({"error": "Post body is required"}, status=400)
            post.body = val
        if "pinned" in body:
            post.pinned = bool(body["pinned"])

        post.edited_at = timezone.now()
        update_fields = [f for f in allowed if f in body] + ["edited_at"]
        post.save(update_fields=update_fields)
        return JsonResponse(_post_to_dict(post))

    # DELETE
    if not is_author and not is_admin:
        return JsonResponse({"error": "You can only delete your own posts"}, status=403)
    post.delete()
    return JsonResponse({"ok": True})


# ── Group requests ───────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def group_request_list(request):
    """
    GET  — list your own group requests (or all if site admin).
    POST — submit a new group request.
    """
    if request.method == "GET":
        if request.user.is_staff:
            qs = GroupRequest.objects.select_related("requester").all()
        else:
            qs = GroupRequest.objects.filter(requester=request.user)
        return JsonResponse([
            {
                "id": r.id,
                "group_name": r.group_name,
                "contact_email": r.contact_email,
                "comments": r.comments,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "requester": r.requester.username,
            }
            for r in qs
        ], safe=False)

    # POST
    body, err = _parse_json(request)
    if err:
        return err

    group_name = body.get("group_name", "").strip()
    contact_email = body.get("contact_email", "").strip()
    if not group_name:
        return JsonResponse({"error": "group_name is required"}, status=400)
    if not contact_email:
        return JsonResponse({"error": "contact_email is required"}, status=400)

    gr = GroupRequest.objects.create(
        requester=request.user,
        group_name=group_name,
        contact_email=contact_email,
        comments=body.get("comments", ""),
    )
    return JsonResponse({
        "id": gr.id,
        "group_name": gr.group_name,
        "contact_email": gr.contact_email,
        "comments": gr.comments,
        "status": gr.status,
        "created_at": gr.created_at.isoformat(),
    }, status=201)


@login_required
@require_http_methods(["PATCH"])
def group_request_review(request, request_id):
    """PATCH — approve or reject a group request (site admin only)."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Only site admins can review group requests"}, status=403)

    gr = get_object_or_404(GroupRequest, id=request_id)

    body, err = _parse_json(request)
    if err:
        return err

    new_status = body.get("status")
    valid = {GroupRequest.Status.APPROVED, GroupRequest.Status.REJECTED}
    if new_status not in valid:
        return JsonResponse(
            {"error": f"status must be one of: {', '.join(sorted(valid))}"},
            status=400,
        )

    gr.status = new_status
    gr.reviewed_at = timezone.now()
    gr.reviewed_by = request.user
    gr.save(update_fields=["status", "reviewed_at", "reviewed_by"])

    return JsonResponse({
        "id": gr.id,
        "group_name": gr.group_name,
        "status": gr.status,
        "reviewed_at": gr.reviewed_at.isoformat(),
        "reviewed_by": gr.reviewed_by.username,
    })

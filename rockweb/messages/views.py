import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q, Subquery, OuterRef, Exists
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Conversation, ConversationMember, Message, MessageAttachment

User = get_user_model()

# ── helpers ──────────────────────────────────────────────────

def _parse_json(request):
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


def _conversation_to_dict(conversation, user):
    members = list(
        conversation.memberships.select_related("user").values_list(
            "user__id", "user__username", "role",
        )
    )
    membership = next((m for m in members if m[0] == user.id), None)

    last_message = (
        conversation.messages.order_by("-created_at")
        .values("id", "body", "sender__username", "created_at")
        .first()
    )

    # Unread count: messages after last_read_at
    unread = 0
    if membership:
        member_obj = conversation.memberships.filter(user=user).first()
        if member_obj and member_obj.last_read_at:
            unread = conversation.messages.filter(
                created_at__gt=member_obj.last_read_at,
            ).exclude(sender=user).count()
        elif member_obj:
            unread = conversation.messages.exclude(sender=user).count()

    return {
        "id": conversation.id,
        "title": conversation.title,
        "is_group": conversation.is_group,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "members": [
            {"id": uid, "username": uname, "role": role}
            for uid, uname, role in members
        ],
        "last_message": {
            "id": last_message["id"],
            "body": last_message["body"][:100],
            "sender": last_message["sender__username"],
            "created_at": last_message["created_at"].isoformat(),
        } if last_message else None,
        "unread_count": unread,
    }


def _message_to_dict(message):
    data = {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender": {
            "id": message.sender.id,
            "username": message.sender.username,
        } if message.sender else None,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "is_system": message.is_system,
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "file_url": a.file_url,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
            }
            for a in message.attachments.all()
        ],
    }
    return data


def _require_membership(user, conversation):
    """Return the membership or a 403 JsonResponse."""
    try:
        return conversation.memberships.get(user=user), None
    except ConversationMember.DoesNotExist:
        return None, JsonResponse({"error": "Not a member of this conversation"}, status=403)


# ── Conversations ────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def conversation_list(request):
    """
    GET  — list conversations the current user belongs to.
    POST — create a new conversation.
    """
    if request.method == "GET":
        convos = (
            Conversation.objects
            .filter(memberships__user=request.user)
            .distinct()
            .order_by("-updated_at")
        )
        return JsonResponse(
            [_conversation_to_dict(c, request.user) for c in convos],
            safe=False,
        )

    # POST — create
    body, err = _parse_json(request)
    if err:
        return err

    member_ids = body.get("member_ids", [])
    if not isinstance(member_ids, list):
        return JsonResponse({"error": "member_ids must be a list"}, status=400)

    # Always include the creator
    member_ids_set = set(member_ids) | {request.user.id}
    users = User.objects.filter(id__in=member_ids_set)
    if users.count() < 2:
        return JsonResponse({"error": "A conversation requires at least 2 members"}, status=400)

    is_group = len(member_ids_set) > 2 or body.get("is_group", False)
    title = body.get("title", "")

    # For 1-on-1 chats, prevent duplicates
    if not is_group and len(member_ids_set) == 2:
        other_id = (member_ids_set - {request.user.id}).pop()
        existing = (
            Conversation.objects
            .filter(is_group=False)
            .filter(memberships__user=request.user)
            .filter(memberships__user_id=other_id)
            .first()
        )
        if existing:
            return JsonResponse(_conversation_to_dict(existing, request.user), status=200)

    conversation = Conversation.objects.create(title=title, is_group=is_group)
    ConversationMember.objects.create(
        conversation=conversation, user=request.user, role=ConversationMember.Role.OWNER,
    )
    for u in users.exclude(id=request.user.id):
        ConversationMember.objects.create(conversation=conversation, user=u)

    return JsonResponse(_conversation_to_dict(conversation, request.user), status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def conversation_detail(request, conversation_id):
    """
    GET    — conversation metadata.
    PATCH  — update title (group only, admin/owner).
    DELETE — leave the conversation.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    membership, err = _require_membership(request.user, conversation)
    if err:
        return err

    if request.method == "GET":
        return JsonResponse(_conversation_to_dict(conversation, request.user))

    if request.method == "PATCH":
        if not conversation.is_group:
            return JsonResponse({"error": "Cannot rename a direct conversation"}, status=400)
        if membership.role not in (ConversationMember.Role.ADMIN, ConversationMember.Role.OWNER):
            return JsonResponse({"error": "Only admins and owners can update the conversation"}, status=403)
        body, err = _parse_json(request)
        if err:
            return err
        allowed = {"title"}
        unknown = set(body.keys()) - allowed
        if unknown:
            return JsonResponse({"error": f"Cannot update fields: {', '.join(sorted(unknown))}"}, status=400)
        if "title" in body:
            conversation.title = body["title"]
            conversation.save(update_fields=["title"])
        return JsonResponse(_conversation_to_dict(conversation, request.user))

    # DELETE — leave
    membership.delete()
    # If no members remain, clean up the conversation
    if not conversation.memberships.exists():
        conversation.delete()
    return JsonResponse({"ok": True}, status=200)


# ── Members ──────────────────────────────────────────────────

@login_required
@require_http_methods(["POST", "DELETE"])
def conversation_members(request, conversation_id):
    """
    POST   — add a member (admin/owner, group only).
    DELETE — remove a member (admin/owner, or self).
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    membership, err = _require_membership(request.user, conversation)
    if err:
        return err

    body, err = _parse_json(request)
    if err:
        return err

    user_id = body.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id is required"}, status=400)

    target_user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        if not conversation.is_group:
            return JsonResponse({"error": "Cannot add members to a direct conversation"}, status=400)
        if membership.role not in (ConversationMember.Role.ADMIN, ConversationMember.Role.OWNER):
            return JsonResponse({"error": "Only admins and owners can add members"}, status=403)
        _, created = ConversationMember.objects.get_or_create(
            conversation=conversation, user=target_user,
        )
        if not created:
            return JsonResponse({"error": "User is already a member"}, status=409)
        return JsonResponse(_conversation_to_dict(conversation, request.user), status=201)

    # DELETE — remove member
    is_self = target_user == request.user
    is_privileged = membership.role in (ConversationMember.Role.ADMIN, ConversationMember.Role.OWNER)
    if not is_self and not is_privileged:
        return JsonResponse({"error": "You can only remove yourself or require admin/owner role"}, status=403)
    ConversationMember.objects.filter(conversation=conversation, user=target_user).delete()
    if not conversation.memberships.exists():
        conversation.delete()
        return JsonResponse({"ok": True})
    return JsonResponse(_conversation_to_dict(conversation, request.user))


# ── Messages ─────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def message_list(request, conversation_id):
    """
    GET  — list messages (paginated via ?before=<id>&limit=N).
    POST — send a message.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    _, err = _require_membership(request.user, conversation)
    if err:
        return err

    if request.method == "GET":
        qs = conversation.messages.select_related("sender").prefetch_related("attachments")

        before = request.GET.get("before")
        if before:
            try:
                cursor_msg = Message.objects.get(id=int(before), conversation=conversation)
                qs = qs.filter(created_at__lt=cursor_msg.created_at)
            except (Message.DoesNotExist, ValueError):
                return JsonResponse({"error": "Invalid 'before' cursor"}, status=400)

        limit = min(int(request.GET.get("limit", 50)), 100)
        messages = list(qs.order_by("-created_at")[:limit])
        messages.reverse()

        return JsonResponse(
            [_message_to_dict(m) for m in messages],
            safe=False,
        )

    # POST — send
    body, err = _parse_json(request)
    if err:
        return err

    text = body.get("body", "").strip()
    if not text:
        return JsonResponse({"error": "Message body is required"}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        body=text,
    )

    # Bump conversation's updated_at
    conversation.save(update_fields=["updated_at"])

    return JsonResponse(_message_to_dict(message), status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def message_detail(request, conversation_id, message_id):
    """
    GET    — single message.
    PATCH  — edit own message body.
    DELETE — delete own message (or admin/owner can delete any).
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    membership, err = _require_membership(request.user, conversation)
    if err:
        return err

    message = get_object_or_404(
        Message.objects.select_related("sender").prefetch_related("attachments"),
        id=message_id,
        conversation=conversation,
    )

    if request.method == "GET":
        return JsonResponse(_message_to_dict(message))

    if request.method == "PATCH":
        if message.sender != request.user:
            return JsonResponse({"error": "You can only edit your own messages"}, status=403)
        body, err = _parse_json(request)
        if err:
            return err
        text = body.get("body", "").strip()
        if not text:
            return JsonResponse({"error": "Message body is required"}, status=400)
        message.body = text
        message.edited_at = timezone.now()
        message.save(update_fields=["body", "edited_at"])
        return JsonResponse(_message_to_dict(message))

    # DELETE
    is_privileged = membership.role in (ConversationMember.Role.ADMIN, ConversationMember.Role.OWNER)
    if message.sender != request.user and not is_privileged:
        return JsonResponse({"error": "You can only delete your own messages"}, status=403)
    message.delete()
    return JsonResponse({"ok": True})


# ── Read receipts ────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def mark_read(request, conversation_id):
    """POST — mark the conversation as read up to now."""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    membership, err = _require_membership(request.user, conversation)
    if err:
        return err

    membership.last_read_at = timezone.now()
    membership.save(update_fields=["last_read_at"])
    return JsonResponse({"ok": True, "last_read_at": membership.last_read_at.isoformat()})


# ── Search ───────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def search_messages(request):
    """GET /api/messages/search/?q=term — full-text search across user's conversations."""
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"error": "Query parameter 'q' is required"}, status=400)

    user_conversations = Conversation.objects.filter(memberships__user=request.user)
    results = (
        Message.objects
        .filter(conversation__in=user_conversations)
        .filter(body__icontains=query)
        .select_related("sender", "conversation")
        .order_by("-created_at")[:25]
    )

    return JsonResponse([
        {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "conversation_title": m.conversation.title,
            "sender": m.sender.username if m.sender else None,
            "body": m.body,
            "created_at": m.created_at.isoformat(),
        }
        for m in results
    ], safe=False)

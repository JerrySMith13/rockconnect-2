from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class Conversation(models.Model):
    """A chat thread — works for both 1-on-1 and group conversations."""

    title = models.CharField(max_length=255, blank=True)
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ConversationMember",
        related_name="conversations",
    )

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["-updated_at"], name="conv_updated_desc"),
        ]

    def __str__(self):
        return self.title or f"Conversation {self.pk}"


class ConversationMember(models.Model):
    """Per-user state within a conversation (read cursor, role, etc.)."""

    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        ADMIN = "admin", "Admin"
        OWNER = "owner", "Owner"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="unique_conversation_member",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "conversation"],
                name="member_user_conv",
            ),
        ]

    def __str__(self):
        return f"{self.user} in {self.conversation}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_system = models.BooleanField(
        default=False,
        help_text="True for auto-generated events (user joined, etc.)",
    )
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["conversation", "-created_at"],
                name="msg_conv_created_desc",
            ),
            models.Index(
                fields=["conversation", "created_at"],
                name="msg_conv_created_asc",
            ),
            GinIndex(
                fields=["search_vector"],
                name="msg_search_vector_gin",
            ),
        ]

    def __str__(self):
        preview = self.body[:50] if self.body else ""
        return f"{self.sender}: {preview}"


class MessageAttachment(models.Model):
    """File or link attached to a message."""

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    filename = models.CharField(max_length=255)
    file_url = models.URLField(max_length=500)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

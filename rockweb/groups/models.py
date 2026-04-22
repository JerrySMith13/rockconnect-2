from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class Group(models.Model):
    """A community group managed by admins."""

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class PostPermission(models.TextChoices):
        ANYONE = "anyone", "Any member"
        ADMINS = "admins", "Admins only"

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    bio = models.TextField(blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    post_permission = models.CharField(
        max_length=10,
        choices=PostPermission.choices,
        default=PostPermission.ANYONE,
        help_text="Who is allowed to create posts in this group.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="GroupMember",
        related_name="user_groups",
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"], name="group_slug"),
            models.Index(fields=["visibility"], name="group_visibility"),
            models.Index(fields=["-created_at"], name="group_created_desc"),
        ]

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    """
    Join table linking users to groups.

    Admins are regular user accounts granted the 'admin' role within a group.
    Only site-wide staff/superusers can create groups, but group-level admins
    manage membership and content.
    """

    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        ADMIN = "admin", "Admin"

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    nickname = models.CharField(max_length=100, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                name="unique_group_member",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "group"], name="gmember_user_group"),
        ]

    def __str__(self):
        label = self.nickname or self.user
        return f"{label} in {self.group}"


class GroupPost(models.Model):
    """A post within a group, created by a member (subject to post_permission)."""

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="group_posts",
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    pinned = models.BooleanField(default=False)
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        ordering = ["-pinned", "-created_at"]
        indexes = [
            models.Index(
                fields=["group", "-created_at"],
                name="gpost_group_created_desc",
            ),
            models.Index(
                fields=["group", "-pinned", "-created_at"],
                name="gpost_group_pinned_created",
            ),
            GinIndex(
                fields=["search_vector"],
                name="gpost_search_vector_gin",
            ),
        ]

    def __str__(self):
        return self.title


class GroupRequest(models.Model):
    """
    A request to create a new group, submitted by any user.

    Reviewed by site admins via the Django admin interface.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_requests",
    )
    group_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    comments = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_group_requests",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="greq_status_created"),
        ]

    def __str__(self):
        return f"{self.group_name} ({self.status})"

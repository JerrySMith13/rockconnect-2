from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Group, GroupMember, GroupPost, GroupRequest


class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 1
    fields = ("user", "role", "nickname", "joined_at")
    readonly_fields = ("joined_at",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "visibility", "post_permission", "member_count", "frontend_link", "created_at")
    list_filter = ("visibility", "post_permission")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [GroupMemberInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "bio", "thumbnail_url")}),
        ("Access Control", {"fields": ("visibility", "post_permission")}),
    )

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.memberships.count()

    @admin.display(description="View on site")
    def frontend_link(self, obj):
        url = reverse("group-detail-page", kwargs={"group_slug": obj.slug})
        return format_html('<a href="{}" target="_blank">View</a>', url)


@admin.register(GroupPost)
class GroupPostAdmin(admin.ModelAdmin):
    list_display = ("title", "group", "author", "pinned", "created_at")
    list_filter = ("group", "pinned")
    search_fields = ("title", "body")
    list_editable = ("pinned",)
    readonly_fields = ("created_at", "edited_at")


@admin.register(GroupRequest)
class GroupRequestAdmin(admin.ModelAdmin):
    list_display = ("group_name", "requester", "contact_email", "status", "created_at", "reviewed_by")
    list_filter = ("status",)
    list_editable = ("status",)
    search_fields = ("group_name", "contact_email")
    readonly_fields = ("requester", "group_name", "contact_email", "comments", "created_at")
    fieldsets = (
        ("Request Details", {
            "fields": ("requester", "group_name", "contact_email", "comments", "created_at"),
        }),
        ("Review", {
            "fields": ("status", "reviewed_at", "reviewed_by"),
        }),
    )

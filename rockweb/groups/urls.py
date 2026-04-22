from django.urls import path

from . import views

app_name = "groups"
urlpatterns = [
    # Group requests (before slug capture to avoid collision)
    path("requests/", views.group_request_list, name="group-request-list"),
    path("requests/<int:request_id>/review/", views.group_request_review, name="group-request-review"),

    # Groups
    path("", views.group_list, name="group-list"),
    path("<slug:group_slug>/", views.group_detail, name="group-detail"),

    # Members
    path("<slug:group_slug>/members/", views.group_members, name="group-members"),
    path("<slug:group_slug>/members/settings/", views.member_settings, name="member-settings"),
    path("<slug:group_slug>/members/role/", views.member_role, name="member-role"),

    # Posts
    path("<slug:group_slug>/posts/", views.post_list, name="post-list"),
    path("<slug:group_slug>/posts/<int:post_id>/", views.post_detail, name="post-detail"),
]

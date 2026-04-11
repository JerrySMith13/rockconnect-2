from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("", views.conversation_list, name="conversation-list"),
    path("<int:conversation_id>/", views.conversation_detail, name="conversation-detail"),
    path("<int:conversation_id>/members/", views.conversation_members, name="conversation-members"),
    path("<int:conversation_id>/messages/", views.message_list, name="message-list"),
    path("<int:conversation_id>/messages/<int:message_id>/", views.message_detail, name="message-detail"),
    path("<int:conversation_id>/read/", views.mark_read, name="mark-read"),
    path("search/", views.search_messages, name="search-messages"),
]

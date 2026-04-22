from django.urls import include, path

from users import views as user_views

app_name = "api"
urlpatterns = [
    path("users/me/", user_views.api_me, name="user-me"),
    path("users/<str:username>/", user_views.api_user_detail, name="user-detail"),
    path("conversations/", include("messages.urls")),
    path("groups/", include("groups.urls")),
]

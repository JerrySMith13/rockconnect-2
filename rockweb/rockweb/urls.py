"""
URL configuration for rockweb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

from groups.views import group_admin_page, group_detail_page, group_list_page, group_request_page
from messages.views import chat_page


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("users:profile", username=request.user.username)
    return redirect("account_login")


urlpatterns = [
    path("", root_redirect, name="root"),
    path("chat/", chat_page, name="chat"),
    path("groups/", group_list_page, name="group-list-page"),
    path("groups/request/", group_request_page, name="group-request-page"),
    path("groups/<slug:group_slug>/", group_detail_page, name="group-detail-page"),
    path("groups/<slug:group_slug>/admin/", group_admin_page, name="group-admin-page"),
    path("users/", include("users.urls")),
    path("api/", include("api.urls")),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]

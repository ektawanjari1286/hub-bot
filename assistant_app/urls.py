
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("chat/", views.chat_api, name="chat_api"),
    path("chat/history/", views.chat_history_api, name="chat_history_api"),
    path("chat/history/clear/", views.clear_chat_history_api, name="clear_chat_history_api"),
    path("logout/", views.logout_page, name="logout"),
]

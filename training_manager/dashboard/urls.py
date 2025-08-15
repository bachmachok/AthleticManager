from django.urls import path
from . import views

urlpatterns = [
    # --- Публічні ---
    path("", views.index, name="index"),
    path("login/", views.login_request_code, name="login"),
    path("verify-otp/", views.verify_code, name="verify_code"),
    path("set-language/", views.settings_view, name="set_language"),  # якщо маєш окремий set_language, лиши його

    # --- Приватні (доступ під логіном; декоратори вже у views.py) ---
    path("home/", views.dashboard_home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("library/", views.library_view, name="library"),
    path("settings/", views.settings_view, name="settings"),
    path("logout/", views.logout_view, name="logout"),

    # --- Категорії ---
    path("category/edit/<int:category_id>/", views.edit_category, name="edit_category"),
    path("category/delete/<int:category_id>/", views.delete_category, name="delete_category"),

    # --- Відео ---
    path("video/edit/<int:video_id>/", views.edit_video, name="edit_video"),
    path("video/delete/<int:video_id>/", views.delete_video, name="delete_video"),

    # --- Debug endpoints (RSS only) ---
    path("debug/news", views.debug_news, name="debug_news"),
]

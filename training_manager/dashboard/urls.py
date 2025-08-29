# training_manager/dashboard/urls.py
from django.urls import path
from django.views.i18n import set_language, JavaScriptCatalog  # + JS i18n
from . import views

urlpatterns = [
    # --- Публічні ---
    path("", views.index, name="index"),
    path("login/", views.login_request_code, name="login"),
    path("verify-otp/", views.verify_code, name="verify_code"),

    # --- I18N / тема ---
    path("i18n/set-language/", set_language, name="set_language"),
    path("i18n/set-theme/", views.set_theme, name="set_theme"),
    path("i18n/js/", JavaScriptCatalog.as_view(packages=("dashboard",)), name="jsi18n"),

    # --- Приватні ---
    path("home/", views.dashboard_home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("library/", views.library_view, name="library"),
    path("logout/", views.logout_view, name="logout"),

    # --- Категорії ---
    path("category/edit/<int:category_id>/", views.edit_category, name="edit_category"),
    path("category/delete/<int:category_id>/", views.delete_category, name="delete_category"),
    path("library/category/<int:pk>/", views.category_detail, name="category_detail"),

    # --- Відео ---
    path("video/edit/<int:video_id>/", views.edit_video, name="edit_video"),
    path("video/delete/<int:video_id>/", views.delete_video, name="delete_video"),

    # --- Анотації ---
    path("annotations/", views.annotations_list, name="annotations_list"),
    path("annotate/<int:video_id>/", views.annotate_video, name="annotate_video"),
    path("api/videos/<int:video_id>/annotations/", views.annotations_api, name="annotations_api"),

    # --- Debug ---
    path("debug/news", views.debug_news, name="debug_news"),
]

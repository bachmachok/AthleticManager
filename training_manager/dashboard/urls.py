from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('upload/', views.upload, name='upload'),
    path('library/', views.library_view, name='library'),

    # Редагування та видалення категорій
    path('category/edit/<int:category_id>/', views.edit_category, name='edit_category'),
    path('category/delete/<int:category_id>/', views.delete_category, name='delete_category'),

    # Редагування та видалення відео
    path('video/edit/<int:video_id>/', views.edit_video, name='edit_video'),
    path('video/delete/<int:video_id>/', views.delete_video, name='delete_video'),
]

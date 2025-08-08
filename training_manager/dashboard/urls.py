from django.urls import path
from django.contrib.auth.decorators import login_required
from django.conf.urls.i18n import set_language
from . import views

urlpatterns = [
    # Публічні
    path('', views.index, name='index'),
    path('login/', views.login_request_code, name='login'),
    path('verify-otp/', views.verify_code, name='verify_code'),
    path('set-language/', set_language, name='set_language'),

    # Приватні
    path('home/', login_required(views.home), name='home'),
    path('upload/', login_required(views.upload), name='upload'),
    path('library/', login_required(views.library_view), name='library'),
    path('settings/', login_required(views.settings_view), name='settings'),
    path('logout/', views.logout_view, name='logout'),

    # Категорії
    path('category/edit/<int:category_id>/', login_required(views.edit_category), name='edit_category'),
    path('category/delete/<int:category_id>/', login_required(views.delete_category), name='delete_category'),

    # Відео
    path('video/edit/<int:video_id>/', login_required(views.edit_video), name='edit_video'),
    path('video/delete/<int:video_id>/', login_required(views.delete_video), name='delete_video'),
]

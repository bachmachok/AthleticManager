from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.utils.translation import activate, get_language
from django.http import HttpResponseRedirect, JsonResponse
from django.conf import settings
import logging

# LIVE-дані (RSS) — лише новини
from .utils import fetch_sport_news

# Пошта
from .gmail_api import send_gmail

# Моделі/форми
from .models import AttemptCategory, AttemptVideo, OTPCode
from .forms import (
    AttemptCategoryForm,
    AttemptVideoForm,
    OTPRequestForm,
    OTPVerifyForm,
)

logger = logging.getLogger(__name__)


# -------------------------
# ПУБЛІЧНА ГОЛОВНА (LIVE)
# -------------------------
def index(request):
    """
    Головна: відео + новини (RSS).
    """
    lang = get_language() or settings.LANGUAGE_CODE
    feeds = getattr(settings, "SPORT_NEWS_FEEDS_MAP", {}).get(lang, settings.SPORT_NEWS_FEEDS)

    news = fetch_sport_news(limit=9, feeds=feeds)

    return render(request, "dashboard/index.html", {
        "news": news,
        # results більше не використовуємо — таблицю робимо статично в шаблоні
    })


# -------------------------
# OTP-ЛОГІН (вхід по коду)
# -------------------------
def login_request_code(request):
    """
    Форма запиту коду для входу (OTP).
    Надсилаємо код на email через Gmail API, зберігаємо user_id і last_code в сесії.
    """
    next_url = request.GET.get('next')
    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user, _ = User.objects.get_or_create(username=email, email=email)

            code = get_random_string(length=6, allowed_chars='1234567890')
            OTPCode.objects.create(user=user, code=code)

            request.session['user_id'] = user.id
            request.session['last_code'] = code
            if next_url:
                request.session['next_url'] = next_url

            try:
                send_gmail(
                    to_email=email,
                    subject='Ваш код підтвердження',
                    body=f'Ваш код: {code}',
                )
            except Exception as e:
                logger.exception("Не вдалося надіслати лист: %s", e)

            return redirect('verify_code')
    else:
        form = OTPRequestForm()

    return render(request, 'dashboard/request_code.html', {
        'form': form,
        'mode': 'login',
        'next': next_url,
    })


def verify_code(request):
    """
    Введення та перевірка OTP-коду.
    При успіху — логін, редірект на next або на index.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            otp = OTPCode.objects.filter(user=user, code=code).order_by('-created_at').first()

            logger.info(f"[DEBUG] Введений код: {code}")
            logger.info(f"[DEBUG] Код із сесії: {request.session.get('last_code')}")
            logger.info(f"[DEBUG] OTP у базі знайдено: {bool(otp)}")
            logger.info(f"[DEBUG] OTP прострочений: {otp.is_expired() if otp else 'N/A'}")

            if otp and not otp.is_expired():
                login(request, user)
                request.session.pop('last_code', None)
                request.session.pop('user_id', None)
                next_url = request.session.pop('next_url', None)
                return redirect(next_url or 'index')
            else:
                form.add_error(None, 'Невірний або прострочений код.')
    else:
        form = OTPVerifyForm()

    return render(request, 'dashboard/verify_code.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# -------------------------
# ВНУТРІШНІ СТОРІНКИ (під логіном)
# -------------------------
@login_required
def dashboard_home(request):
    """Внутрішня домашня сторінка (за потреби)."""
    return render(request, 'dashboard/home.html')


@login_required
def upload(request):
    """
    Додавання категорій та відео, перелік категорій і відео.
    """
    if request.method == 'POST':
        if 'create_category' in request.POST:
            category_form = AttemptCategoryForm(request.POST)
            video_form = AttemptVideoForm()
            if category_form.is_valid():
                category_form.save()
                return redirect('upload')

        elif 'add_video' in request.POST:
            category_form = AttemptCategoryForm()
            video_form = AttemptVideoForm(request.POST, request.FILES)
            if video_form.is_valid():
                video_form.save()
                return redirect('upload')
    else:
        category_form = AttemptCategoryForm()
        video_form = AttemptVideoForm()

    categories = AttemptCategory.objects.all().order_by('-date')
    videos = AttemptVideo.objects.select_related('category').all().order_by('-id')

    return render(request, 'dashboard/upload.html', {
        'category_form': category_form,
        'video_form': video_form,
        'categories': categories,
        'videos': videos,
    })


@login_required
def library_view(request):
    """
    Відображення бібліотеки відео з фільтром по типу події (event_type).
    """
    filter_event = request.GET.get('event')
    videos_qs = AttemptVideo.objects.all()
    if filter_event:
        videos_qs = videos_qs.filter(event_type=filter_event)

    categories = AttemptCategory.objects.prefetch_related(
        Prefetch('videos', queryset=videos_qs)
    ).order_by('-date')

    return render(request, 'dashboard/library.html', {
        'categories': categories,
        'filter_event': filter_event,
    })


@require_http_methods(["GET", "POST"])
@login_required
def edit_category(request, category_id):
    category = get_object_or_404(AttemptCategory, id=category_id)
    if request.method == 'POST':
        form = AttemptCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('upload')
    else:
        form = AttemptCategoryForm(instance=category)

    return render(request, 'dashboard/edit_category.html', {'form': form})


@require_http_methods(["GET", "POST"])
@login_required
def edit_video(request, video_id):
    video = get_object_or_404(AttemptVideo, id=video_id)
    if request.method == 'POST':
        form = AttemptVideoForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            form.save()
            return redirect('upload')
    else:
        form = AttemptVideoForm(instance=video)

    return render(request, 'dashboard/edit_video.html', {'form': form})


@require_POST
@login_required
def delete_category(request, category_id):
    category = get_object_or_404(AttemptCategory, id=category_id)
    category.delete()
    return redirect('upload')


@require_POST
@login_required
def delete_video(request, video_id):
    video = get_object_or_404(AttemptVideo, id=video_id)
    video.delete()
    return redirect('upload')


@login_required
def settings_view(request):
    """
    Налаштування мови/теми. Активує мову, зберігає cookie для мови і тему в сесію.
    """
    if request.method == 'POST':
        language = request.POST.get('language')
        theme = request.POST.get('theme', 'light')

        if language in dict(settings.LANGUAGES).keys():
            activate(language)
            response = HttpResponseRedirect(request.path)
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
            request.session['theme'] = theme
            return response

    languages = settings.LANGUAGES
    current_language = get_language()
    current_theme = request.session.get('theme', 'light')

    return render(request, 'dashboard/settings.html', {
        'languages': languages,
        'current_language': current_language,
        'current_theme': current_theme,
    })


# -------------------------
# DEBUG-ЕНДПОЇНТИ (опційно)
# -------------------------
def debug_news(request):
    """
    GET /debug/news — перевірка RSS. Повертає JSON із 5 останніх.
    """
    items = fetch_sport_news(limit=5)
    serialized = [
        {
            **i,
            "date": i["date"].isoformat() if i.get("date") else None
        } for i in items
    ]
    return JsonResponse({"ok": True, "count": len(serialized), "items": serialized})

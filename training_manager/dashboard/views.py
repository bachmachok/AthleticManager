import json
import logging
import hmac
from datetime import timedelta

from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import activate, get_language
from django.views.decorators.http import require_http_methods, require_POST

from rest_framework_simplejwt.tokens import RefreshToken

from .models import AttemptCategory, AttemptVideo, AttemptVideoAnnotation, OTPCode
from .utils import fetch_sport_news
from .gmail_api import send_gmail
from .forms import (
    AttemptCategoryForm,
    AttemptVideoForm,
    OTPRequestForm,
    OTPVerifyForm,
)


logger = logging.getLogger(__name__)

ACCESS_MAX_AGE = int(getattr(settings, "SIMPLE_JWT", {}).get("ACCESS_TOKEN_LIFETIME", timedelta(minutes=30)).total_seconds())
REFRESH_MAX_AGE = int(getattr(settings, "SIMPLE_JWT", {}).get("REFRESH_TOKEN_LIFETIME", timedelta(days=7)).total_seconds())

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



def set_jwt_cookies(response, user):
    """
    Видає refresh+access токени у HttpOnly-куках.
    """
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    secure_cookie = not settings.DEBUG  # у продакшені буде True
    response.set_cookie(
        key="access_token",
        value=str(access),
        max_age=ACCESS_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=secure_cookie,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=str(refresh),
        max_age=REFRESH_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=secure_cookie,
        path="/",
    )
    return response

def clear_jwt_cookies(response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response


# -------------------------
# OTP-ЛОГІН (вхід по коду)
# -------------------------
def login_request_code(request):
    """
    Крок 1: вводиш email -> шлемо OTP і кладемо в сесію ЛИШЕ otp_id (без user_id/коду).
    """
    next_url = request.GET.get('next')
    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user, _ = User.objects.get_or_create(username=email, email=email)

            code = get_random_string(length=6, allowed_chars='1234567890')

            with transaction.atomic():
                otp = OTPCode.objects.create(user=user, code=code)
                request.session['otp_id'] = otp.id                     # ✅ тільки otp_id
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
                form.add_error(None, "Не вдалося надіслати лист. Спробуйте ще раз.")
                return render(request, 'dashboard/request_code.html', {
                    'form': form, 'mode': 'login', 'next': next_url,
                })

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
    Крок 2: вводиш OTP -> якщо валідний і не прострочений, ставимо JWT у HttpOnly-куки
    (і логінимо сесію, щоб існуючі @login_required сторінки працювали як раніше).
    """
    otp_id = request.session.get('otp_id')
    if not otp_id:
        return redirect('login')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']

            otp = get_object_or_404(OTPCode, id=otp_id)
            user = otp.user

            logger.info(f"[DEBUG] Введений код: {code}; OTP існує: {bool(otp)}; прострочений: {otp.is_expired()}")

            valid = (not otp.is_expired()) and hmac.compare_digest(otp.code, code)
            if valid:
                # 1) (опційно) сесійний логін для існуючих вʼюх
                django_login(request, user)

                # 2) redirect з виставленням JWT-куків
                next_url = request.session.pop('next_url', None)
                request.session.pop('otp_id', None)

                response = redirect(next_url or 'index')
                set_jwt_cookies(response, user)
                return response

            form.add_error(None, 'Невірний або прострочений код.')
    else:
        form = OTPVerifyForm()

    return render(request, 'dashboard/verify_code.html', {'form': form})


def logout_view(request):
    """
    Вихід: чистимо JWT-куки та сесію.
    (якщо треба, можеш ще блэклістити refresh — розкоментуй у майбутньому)
    """
    response = redirect('login')
    clear_jwt_cookies(response)
    django_logout(request)
    return response


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
    Додавання категорій та відео + список існуючих.
    Після успішного сабміту повертаємось на відповідну вкладку через hash.
    """
    if request.method == 'POST':
        # Створити/оновити КАТЕГОРІЮ
        if 'create_category' in request.POST:
            category_form = AttemptCategoryForm(request.POST)
            video_form = AttemptVideoForm()  # порожня друга форма
            if category_form.is_valid():
                category_form.save()
                # повертаємось на вкладку "Категорії"
                return HttpResponseRedirect(reverse('upload') + '#categories')

        # Додати ВІДЕО
        elif 'add_video' in request.POST:
            category_form = AttemptCategoryForm()  # порожня друга форма
            video_form = AttemptVideoForm(request.POST, request.FILES)
            if video_form.is_valid():
                video_form.save()
                # повертаємось на вкладку "Відео"
                return HttpResponseRedirect(reverse('upload') + '#videos')

        else:
            # невідомий сабміт — показуємо обидві форми порожні
            category_form = AttemptCategoryForm()
            video_form = AttemptVideoForm()

    else:
        category_form = AttemptCategoryForm()
        video_form = AttemptVideoForm()

    # Списки
    categories = AttemptCategory.objects.all().order_by('-date', 'place')
    videos = (AttemptVideo.objects
              .select_related('category')
              .all()
              .order_by('-id'))

    # метадані для фронту (id + attempt_type) — потрібно для показу/приховування "Місце в протоколі"
    categories_meta = list(AttemptCategory.objects.values('id', 'attempt_type'))

    return render(request, 'dashboard/upload.html', {
        'category_form': category_form,
        'video_form': video_form,
        'categories': categories,
        'videos': videos,
        'categories_meta': categories_meta,
    })



@login_required
def library_view(request):
    """
    Каталог категорій:
      • фільтр за типом категорії (training/competition)
      • сортування (дата/місце/тип/к-сть відео)
      • підрахунок кількості відео в кожній категорії
    """
    # нові параметри із шаблону
    filter_attempt_type = (request.GET.get('attempt_type') or '').strip()
    sort = (request.GET.get('sort') or 'date_desc').strip()

    qs = AttemptCategory.objects.all()

    # фільтр за типом категорії
    valid_types = dict(AttemptCategory.ATTEMPT_TYPE_CHOICES).keys()
    if filter_attempt_type in valid_types:
        qs = qs.filter(attempt_type=filter_attempt_type)

    # кількість відео (related_name='videos' у FK)
    qs = qs.annotate(videos_count=Count('videos'))

    # сортування
    order_map = {
        'date_desc':   ('-date', 'place'),
        'date_asc':    ('date', 'place'),
        'place_asc':   ('place', '-date'),
        'place_desc':  ('-place', '-date'),
        'type_asc':    ('attempt_type', '-date'),
        'type_desc':   ('-attempt_type', '-date'),
        'videos_desc': ('-videos_count', '-date'),
        'videos_asc':  ('videos_count', '-date'),
    }
    qs = qs.order_by(*order_map.get(sort, ('-date', 'place')))

    # пагінація
    page_obj = Paginator(qs, 12).get_page(request.GET.get('page'))

    return render(request, 'dashboard/library.html', {
        'categories': page_obj,
        'attempt_type_choices': AttemptCategory.ATTEMPT_TYPE_CHOICES,
        'filter_attempt_type': filter_attempt_type,
        'sort': sort,
    })


@login_required
def category_detail(request, pk: int):
    """
    Сторінка категорії:
      • фільтр за дисципліною відео
      • сортування: спроба ↑/↓, час ↑/↓, додані новіші/старіші,
        + результат (залежно від дисципліни)
      • без сортування за місцем
    """
    category = get_object_or_404(AttemptCategory, pk=pk)

    filter_event = (request.GET.get('event') or '').strip()
    sort = (request.GET.get('sort') or 'attempt_asc').strip()

    videos = AttemptVideo.objects.filter(category=category).select_related('category')
    if filter_event in dict(AttemptVideo.EVENT_CATEGORY_CHOICES):
        videos = videos.filter(event_type=filter_event)

    # мапа "звичайних" сортувань
    base_order_map = {
        'attempt_asc':  ('attempt_number', 'id'),
        'attempt_desc': ('-attempt_number', '-id'),
        'time_asc':     ('time', 'id'),
        'time_desc':    ('-time', '-id'),
        'created_desc': ('-id',),   # новіші першими
        'created_asc':  ('id',),    # старіші першими
    }

    # динамічне сортування за результатом
    if sort in ('result_best', 'result_worst'):
        # коли дисципліна не вибрана — немає уніфікованих одиниць
        if not filter_event:
            # fallback — лишаємо за замовчуванням (спроба ↑)
            order_fields = base_order_map['attempt_asc']
            result_sort_disabled = True
        else:
            result_sort_disabled = False
            if filter_event == 'run':
                # менше — краще
                order_fields = ('result', 'id') if sort == 'result_best' else ('-result', '-id')
            elif filter_event in ('jump', 'throw'):
                # більше — краще
                order_fields = ('-result', '-id') if sort == 'result_best' else ('result', 'id')
            else:
                order_fields = base_order_map['attempt_asc']
    else:
        order_fields = base_order_map.get(sort, base_order_map['attempt_asc'])
        result_sort_disabled = False

    videos = videos.order_by(*order_fields)

    return render(request, 'dashboard/category_detail.html', {
        'category': category,
        'videos': videos,
        'event_choices': AttemptVideo.EVENT_CATEGORY_CHOICES,
        'filter_event': filter_event,
        'sort': sort,
        'result_sort_disabled': result_sort_disabled,
    })


@require_http_methods(["GET", "POST"])
@login_required
def edit_category(request, category_id):
    category = get_object_or_404(AttemptCategory, id=category_id)

    if request.method == 'POST':
        form = AttemptCategoryForm(request.POST, instance=category)
        # якщо користувач змінив тип у формі — беремо з form.data
        is_comp = (form.data.get('attempt_type') == 'competition')
        if form.is_valid():
            form.save()
            return redirect('upload')
    else:
        form = AttemptCategoryForm(instance=category)
        # початковий стан — за поточним значенням у БД
        is_comp = (category.attempt_type == 'competition')

    return render(request, 'dashboard/edit_category.html', {
        'form': form,
        'is_comp': is_comp,
    })

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

    # метадані категорій для фронту (id + attempt_type),
    # щоб ховати/показувати "Місце в протоколі" лише для змагальних
    categories_meta = list(AttemptCategory.objects.values('id', 'attempt_type'))

    return render(request, 'dashboard/edit_video.html', {
        'form': form,
        'categories_meta': categories_meta,
    })


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

@login_required
def annotate_video(request, video_id):
    """
    Перегляд/редагування анотацій конкретного відео.
    Приймає ?from=library або ?from=category&cat=<id>, щоб показати «← Назад».
    """
    video = get_object_or_404(AttemptVideo, id=video_id)

    from_page = request.GET.get('from')
    back_url = None
    if from_page == 'category':
        cat = request.GET.get('cat')
        if cat:
            back_url = reverse('category_detail', args=[cat])
    elif from_page == 'library':
        back_url = reverse('library')

    return render(request, 'dashboard/annotate_video.html', {
        'video': video,
        'back_url': back_url,
    })
@require_http_methods(["GET", "POST"])
@login_required
def annotations_api(request, video_id):
    video = get_object_or_404(AttemptVideo, id=video_id)

    if request.method == "GET":
        ann = getattr(video, 'annotation', None)
        shapes = (ann.data.get("shapes", []) if ann and isinstance(ann.data, dict) else [])
        return JsonResponse({"shapes": shapes})

    # POST
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    shapes = body.get("shapes", None)
    if not isinstance(shapes, list):
        return HttpResponseBadRequest("`shapes` must be a list")

    ann, _ = AttemptVideoAnnotation.objects.get_or_create(video=video)
    ann.data = {"shapes": shapes}
    ann.updated_by = request.user
    ann.save(update_fields=["data", "updated_by", "updated_at"])
    return JsonResponse({"ok": True, "updated_at": ann.updated_at.isoformat()})

@login_required
def annotations_list(request):
    videos = (AttemptVideo.objects
              .select_related('category')
              .order_by('-category__date', 'event_type', 'attempt_number'))
    return render(request, 'dashboard/annotations_list.html', {'videos': videos})
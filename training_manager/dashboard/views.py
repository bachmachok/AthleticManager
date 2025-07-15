from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from .forms import AttemptCategoryForm, AttemptVideoForm
from .models import AttemptCategory, AttemptVideo
from django.db.models import Prefetch


def index(request):
    return render(request, 'dashboard/index.html')


def login_view(request):
    return render(request, 'dashboard/login.html')


def register_view(request):
    return render(request, 'dashboard/register.html')


def upload(request):
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

    context = {
        'category_form': category_form,
        'video_form': video_form,
        'categories': categories,
        'videos': videos,
    }
    return render(request, 'dashboard/upload.html', context)


def library_view(request):
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
def delete_category(request, category_id):
    category = get_object_or_404(AttemptCategory, id=category_id)
    category.delete()
    return redirect('upload')


@require_POST
def delete_video(request, video_id):
    video = get_object_or_404(AttemptVideo, id=video_id)
    video.delete()
    return redirect('upload')

# training_manager/dashboard/models.py
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, RegexValidator, FileExtensionValidator
from django.conf import settings
import datetime


class AttemptCategory(models.Model):
    ATTEMPT_TYPE_CHOICES = [
        ('training', 'Тренувальна'),
        ('competition', 'Змагальна'),
    ]

    attempt_type = models.CharField(
        max_length=20,
        choices=ATTEMPT_TYPE_CHOICES,
        db_index=True,
        verbose_name='Тип спроби'
    )
    # Місце ПРОВЕДЕННЯ (місто/локація) — тільки для категорії
    place = models.CharField(
        max_length=100,
        verbose_name='Місце проведення'
    )
    date = models.DateField(
        verbose_name='Дата',
        db_index=True
    )

    # Зайняте місце (ранг) — потрібно лише для змагальної
    rank = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='Зайняте місце'
    )

    class Meta:
        verbose_name = 'Категорія спроб'
        verbose_name_plural = 'Категорії спроб'
        ordering = ['-date', 'place']

    def __str__(self):
        return f"{self.get_attempt_type_display()} ({self.place}, {self.date:%Y-%m-%d})"


class AttemptVideo(models.Model):
    EVENT_CATEGORY_CHOICES = [
        ('jump', 'Стрибки'),
        ('throw', 'Штовхання/Метання'),
        ('run', 'Біг'),
    ]

    category = models.ForeignKey(
        AttemptCategory,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='Категорія',
        db_index=True
    )
    video = models.FileField(
        upload_to='attempt_videos/',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov', 'm4v', 'avi', 'mkv'])],
        verbose_name='Відео'
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_CATEGORY_CHOICES,
        verbose_name='Дисципліна',
        db_index=True
    )

    # Результат як рядок; одиниці показуємо в UI
    result = models.CharField(
        max_length=20,
        help_text="Результат (м або с)",
        verbose_name='Результат'
    )

    attempt_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Номер спроби'
    )

    # Було: place (NOT NULL)
    # Стало: place_in_protocol (nullable), але зберігаємо старий стовпець БД
    place_in_protocol = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='Місце в протоколі',
        db_column='place',
    )

    time = models.TimeField(
        blank=True,
        null=True,
        help_text="Час спроби (необов’язково)",
        verbose_name='Час спроби'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    class Meta:
        verbose_name = 'Відео спроби'
        verbose_name_plural = 'Відео спроб'
        ordering = ['-category__date', 'event_type', 'attempt_number']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['category', 'attempt_number']),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} — спроба {self.attempt_number} ({self.category})"


class AttemptVideoAnnotation(models.Model):
    video = models.OneToOneField(
        AttemptVideo,
        on_delete=models.CASCADE,
        related_name='annotation',
        verbose_name='Відео'
    )
    data = models.JSONField(default=dict, verbose_name='Дані анотацій')  # {"shapes": [...]}
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Оновлено користувачем'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    class Meta:
        verbose_name = 'Анотації відео'
        verbose_name_plural = 'Анотації відео'

    def __str__(self):
        return f"Annotations for AttemptVideo {self.video_id}"


class OTPCode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_codes',
        verbose_name='Користувач'
    )
    code = models.CharField(
        max_length=6,
        validators=[RegexValidator(r'^\d{6}$', 'Код має складатися з 6 цифр.')],
        verbose_name='Код'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    class Meta:
        verbose_name = 'Одноразовий код'
        verbose_name_plural = 'Одноразові коди'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'code'], name='unique_user_otp_code'),
        ]
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"OTP для {self.user_id} створено {self.created_at:%Y-%m-%d %H:%M:%S}"

    def is_expired(self) -> bool:
        # строк дії 10 хвилин
        return timezone.now() > self.created_at + datetime.timedelta(minutes=10)

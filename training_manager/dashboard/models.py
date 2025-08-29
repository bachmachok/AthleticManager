# training_manager/dashboard/models.py
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, RegexValidator, FileExtensionValidator
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import datetime


class AttemptCategory(models.Model):
    class AttemptType(models.TextChoices):
        TRAINING = 'training', _('Training')
        COMPETITION = 'competition', _('Competition')

    attempt_type = models.CharField(
        max_length=20,
        choices=AttemptType.choices,
        db_index=True,
        verbose_name=_('Attempt type'),
    )
    # Місце проведення (місто/локація)
    place = models.CharField(
        max_length=100,
        verbose_name=_('Place'),
    )
    date = models.DateField(
        verbose_name=_('Date'),
        db_index=True,
    )

    # Зайняте місце (тільки для змагань)
    rank = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        verbose_name=_('Rank in protocol'),
    )

    class Meta:
        verbose_name = _('Attempt category')
        verbose_name_plural = _('Attempt categories')
        ordering = ['-date', 'place']

    def __str__(self):
        return f"{self.get_attempt_type_display()} ({self.place}, {self.date:%Y-%m-%d})"


class AttemptVideo(models.Model):
    class EventType(models.TextChoices):
        JUMP = 'jump', _('Jumps')
        THROW = 'throw', _('Throw/Shot put')
        RUN = 'run', _('Run')

    category = models.ForeignKey(
        AttemptCategory,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name=_('Category'),
        db_index=True,
    )
    video = models.FileField(
        upload_to='attempt_videos/',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov', 'm4v', 'avi', 'mkv'])],
        verbose_name=_('Video'),
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        verbose_name=_('Discipline'),
        db_index=True,
    )

    # Результат як рядок; одиниці показуємо в UI
    result = models.CharField(
        max_length=20,
        help_text=_('Result (m or s)'),
        verbose_name=_('Result'),
    )

    attempt_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Attempt number'),
    )

    # Було: place (NOT NULL). Стало: place_in_protocol (nullable), але залишаємо стовпець БД.
    place_in_protocol = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        verbose_name=_('Place (protocol)'),
        db_column='place',
    )

    time = models.TimeField(
        blank=True,
        null=True,
        help_text=_('Attempt time (optional)'),
        verbose_name=_('Attempt time'),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    class Meta:
        verbose_name = _('Attempt video')
        verbose_name_plural = _('Attempt videos')
        ordering = ['-category__date', 'event_type', 'attempt_number']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['category', 'attempt_number']),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} — #{self.attempt_number} ({self.category})"


class AttemptVideoAnnotation(models.Model):
    video = models.OneToOneField(
        AttemptVideo,
        on_delete=models.CASCADE,
        related_name='annotation',
        verbose_name=_('Video'),
    )
    data = models.JSONField(default=dict, verbose_name=_('Annotation data'))  # {"shapes": [...]}
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('Updated by'),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    class Meta:
        verbose_name = _('Video annotations')
        verbose_name_plural = _('Video annotations')

    def __str__(self):
        return f"Annotations for AttemptVideo {self.video_id}"


class OTPCode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_codes',
        verbose_name=_('User'),
    )
    code = models.CharField(
        max_length=6,
        validators=[RegexValidator(r'^\d{6}$', _('Code must contain 6 digits.'))],
        verbose_name=_('Code'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    class Meta:
        verbose_name = _('One-time code')
        verbose_name_plural = _('One-time codes')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'code'], name='unique_user_otp_code'),
        ]
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"OTP for {self.user_id} created {self.created_at:%Y-%m-%d %H:%M:%S}"

    def is_expired(self) -> bool:
        # строк дії 10 хвилин
        return timezone.now() > self.created_at + datetime.timedelta(minutes=10)

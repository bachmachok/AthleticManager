from django.db import models

class AttemptCategory(models.Model):
    # Категорія: тренувальна чи змагальна спроба
    ATTEMPT_TYPE_CHOICES = [
        ('training', 'Тренувальна'),
        ('competition', 'Змагальна'),
    ]

    attempt_type = models.CharField(max_length=20, choices=ATTEMPT_TYPE_CHOICES)
    place = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return f"{self.get_attempt_type_display()} ({self.place}, {self.date})"


class AttemptVideo(models.Model):
    # Категорії видів змагань
    EVENT_CATEGORY_CHOICES = [
        ('jump', 'Стрибки'),
        ('throw', 'Штовхання/Метання'),
        ('run', 'Біг'),
    ]

    category = models.ForeignKey(AttemptCategory, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(upload_to='attempt_videos/')
    event_type = models.CharField(max_length=20, choices=EVENT_CATEGORY_CHOICES)

    # Результат спроби: метр(м) для стрибків/метань, секунди(с) для бігу, метр(м) для метань —
    # В залежності від категорії використовуємо різні одиниці, але для простоти - зберігаємо як CharField
    result = models.CharField(max_length=20, help_text="Результат (м, с)")

    attempt_number = models.PositiveIntegerField()
    place = models.PositiveIntegerField()
    time = models.TimeField(help_text="Час спроби")

    def __str__(self):
        return f"Відео {self.event_type} - спроба {self.attempt_number} ({self.category})"

# training_manager/dashboard/forms.py
from django import forms
from django.core.validators import RegexValidator
from .models import AttemptCategory, AttemptVideo


# ---- Категорія ----
class AttemptCategoryForm(forms.ModelForm):
    class Meta:
        model = AttemptCategory
        fields = ['attempt_type', 'place', 'date', 'rank']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'rank': forms.NumberInput(attrs={'min': 1}),
        }
        labels = {
            'attempt_type': 'Тип спроби',
            'place': 'Місце проведення',
            'date': 'Дата',
            'rank': 'Зайняте місце',
        }

    def clean(self):
        data = super().clean()
        attempt_type = data.get('attempt_type')
        rank = data.get('rank')

        # rank обовʼязковий лише для змагальної категорії
        if attempt_type == 'competition' and not rank:
            self.add_error('rank', 'Заповніть «Зайняте місце» для змагальної категорії.')
        # для тренувальної — очищаємо
        if attempt_type == 'training':
            data['rank'] = None

        return data


# ---- Відео ----
class AttemptVideoForm(forms.ModelForm):
    class Meta:
        model = AttemptVideo
        fields = ['category', 'video', 'event_type', 'result', 'attempt_number', 'place_in_protocol', 'time']
        widgets = {
            'attempt_number': forms.NumberInput(attrs={'min': 1}),
            'place_in_protocol': forms.NumberInput(attrs={'min': 1}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }
        labels = {
            'category': 'Категорія',
            'video': 'Відео',
            'event_type': 'Дисципліна',
            'result': 'Результат',
            'attempt_number': 'Номер спроби',
            'place_in_protocol': 'Місце в протоколі',
            'time': 'Час спроби',
        }
        help_texts = {
            'result': 'Для бігу — секунди (с), для стрибків/метань — метри (м).',
        }

    def clean(self):
        data = super().clean()
        category = data.get('category')
        place_in_protocol = data.get('place_in_protocol')

        # місце в протоколі потрібне лише для змагальних категорій
        if category and category.attempt_type == 'competition' and not place_in_protocol:
            self.add_error('place_in_protocol', 'Обовʼязкове для змагальної категорії.')
        if category and category.attempt_type == 'training':
            data['place_in_protocol'] = None

        return data


# ---- OTP ----
class OTPRequestForm(forms.Form):
    email = forms.EmailField(label="Електронна пошта")


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        label="Код підтвердження",
        validators=[RegexValidator(r'^\d{6}$', "Код має складатися з 6 цифр.")],
        widget=forms.TextInput(attrs={
            "placeholder": "Введіть 6-значний код",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
        }),
    )

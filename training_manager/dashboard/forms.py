from django import forms
from .models import AttemptCategory, AttemptVideo

# Форма створення категорії спроб
class AttemptCategoryForm(forms.ModelForm):
    class Meta:
        model = AttemptCategory
        fields = ['attempt_type', 'place', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

# Форма додавання відео спроби
class AttemptVideoForm(forms.ModelForm):
    class Meta:
        model = AttemptVideo
        fields = ['category', 'video', 'event_type', 'result', 'attempt_number', 'place', 'time']
        widgets = {
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

# Форма запиту коду OTP (1-й крок)
class OTPRequestForm(forms.Form):
    email = forms.EmailField(label="Електронна пошта")

# Форма підтвердження коду OTP (2-й крок) — без поля email
class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        label="Код підтвердження",
        widget=forms.TextInput(attrs={"placeholder": "Введіть код з електронної пошти"})
    )

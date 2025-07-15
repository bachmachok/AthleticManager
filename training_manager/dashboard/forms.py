from django import forms
from .models import AttemptCategory, AttemptVideo

class AttemptCategoryForm(forms.ModelForm):
    class Meta:
        model = AttemptCategory
        fields = ['attempt_type', 'place', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class AttemptVideoForm(forms.ModelForm):
    class Meta:
        model = AttemptVideo
        fields = ['category', 'video', 'event_type', 'result', 'attempt_number', 'place', 'time']
        widgets = {
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

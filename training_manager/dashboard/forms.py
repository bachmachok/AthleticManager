# training_manager/dashboard/forms.py
from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from .models import AttemptCategory, AttemptVideo


# ---- Категорія ----
class AttemptCategoryForm(forms.ModelForm):
    class Meta:
        model = AttemptCategory
        fields = ["attempt_type", "place", "date", "rank"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "placeholder": _("dd.mm.yyyy")}),
            "rank": forms.NumberInput(attrs={"min": 1}),
        }
        labels = {
            "attempt_type": _("Attempt type"),
            "place": _("Place"),
            "date": _("Date"),
            "rank": _("Rank in protocol"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # перекладний порожній пункт у select
        f = self.fields.get("attempt_type")
        if hasattr(f, "empty_label"):
            f.empty_label = _("---------")

    def clean(self):
        data = super().clean()
        attempt_type = data.get("attempt_type")
        rank = data.get("rank")

        if attempt_type == AttemptCategory.AttemptType.COMPETITION and not rank:
            self.add_error("rank", _("Fill in “Rank in protocol” for competition categories."))
        if attempt_type == AttemptCategory.AttemptType.TRAINING:
            data["rank"] = None

        return data


# ---- Відео ----
class AttemptVideoForm(forms.ModelForm):
    class Meta:
        model = AttemptVideo
        fields = ["category", "video", "event_type", "result", "attempt_number", "place_in_protocol", "time"]
        widgets = {
            "attempt_number": forms.NumberInput(attrs={"min": 1}),
            "place_in_protocol": forms.NumberInput(attrs={"min": 1}),
            "time": forms.TimeInput(attrs={"type": "time", "placeholder": _("hh:mm")}),
        }
        labels = {
            "category":       _("Category"),
            "video":          _("Video"),
            "event_type":     _("Discipline"),
            "result":         _("Result"),
            "attempt_number": _("Attempt number"),
            "place_in_protocol": _("Place in protocol"),
            "time":           _("Attempt time"),
        }
        help_texts = {
            "result": _("For runs — seconds (s); for jumps/throws — meters (m)."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # перекладні пусті пункти у ModelChoice/Choice
        for name in ("category", "event_type"):
            f = self.fields.get(name)
            if hasattr(f, "empty_label"):
                f.empty_label = _("---------")

    def clean(self):
        data = super().clean()
        category = data.get("category")
        place_in_protocol = data.get("place_in_protocol")

        if category and category.attempt_type == AttemptCategory.AttemptType.COMPETITION and not place_in_protocol:
            self.add_error("place_in_protocol", _("Required for competition categories."))
        if category and category.attempt_type == AttemptCategory.AttemptType.TRAINING:
            data["place_in_protocol"] = None

        return data


# ---- OTP ----
class OTPRequestForm(forms.Form):
    email = forms.EmailField(label=_("Email"))


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        label=_("Verification code"),
        validators=[RegexValidator(r"^\d{6}$", _("The code must consist of 6 digits."))],
        widget=forms.TextInput(attrs={
            "placeholder": _("Enter the 6-digit code"),
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
        }),
    )

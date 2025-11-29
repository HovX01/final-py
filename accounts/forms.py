from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms


User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    input_class = "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100"

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", self.input_class)


class EmailAuthenticationForm(AuthenticationForm):
    input_class = "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100"

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", self.input_class)


class VerificationCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={"class": "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100", "placeholder": "Enter 6-digit code"}),
    )

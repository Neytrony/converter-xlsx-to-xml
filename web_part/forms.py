from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Логин",
                "class": "form-control",
            },
        ))
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Пароль",
                "class": "form-control",
            },
        ))
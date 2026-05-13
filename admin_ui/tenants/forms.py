from django import forms


COMMON_INPUT_ATTRS = {
    "class": "w-full rounded-3xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100",
}


class LoginForm(forms.Form):
    username = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"autofocus": True, **COMMON_INPUT_ATTRS}))
    password = forms.CharField(widget=forms.PasswordInput(attrs=COMMON_INPUT_ATTRS))

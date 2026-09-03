from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Account, Category, RecurringTransaction


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=False, label="E-Mail (optional)")

    class Meta:
        model = User
        fields = ("username", "email")


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["name", "account_type", "iban", "starting_balance", "is_archived"]
        widgets = {
            "starting_balance": forms.TextInput(),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "kind", "monthly_budget", "keywords", "color", "icon", "is_archived"]
        widgets = {
            "monthly_budget": forms.TextInput(),
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ["account", "category", "description", "counterparty", "amount", "day_of_month", "is_active"]
        widgets = {
            "amount": forms.TextInput(),
        }

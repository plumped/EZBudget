from django.db import migrations


def backfill_categories(apps, schema_editor):
    Debt = apps.get_model("debts", "Debt")
    Category = apps.get_model("core", "Category")
    for debt in Debt.objects.filter(category__isnull=True):
        category = Category.objects.create(
            name=debt.name,
            kind="debt",
            monthly_budget=debt.minimum_payment,
            is_archived=debt.is_paid_off,
        )
        debt.category = category
        debt.save(update_fields=["category"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("debts", "0002_debt_category_delete_debtpayment"),
    ]

    operations = [
        migrations.RunPython(backfill_categories, noop_reverse),
    ]

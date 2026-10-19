"""Explicit starter plan for secure, time-limited SaaS onboarding."""
from django.db import migrations

def seed_trial_plan(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.get_or_create(
        code="trial",
        defaults={"name":"Пробный доступ (14 дней)","price_minor":0,
                  "max_branches":1,"max_staff":3,"active":True},
    )

class Migration(migrations.Migration):
    dependencies = [("billing","0001_initial")]
    operations = [migrations.RunPython(seed_trial_plan, migrations.RunPython.noop)]

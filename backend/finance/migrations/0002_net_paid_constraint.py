from django.db import migrations, models
from django.db.models import F, Q

class Migration(migrations.Migration):
    dependencies = [("finance", "0001_initial")]
    operations = [
        migrations.RemoveConstraint(model_name="invoice", name="fin_paid_limit"),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.CheckConstraint(
                condition=Q(paid_minor__lte=F("amount_minor") + F("refunded_minor")),
                name="fin_paid_limit",
            ),
        ),
    ]

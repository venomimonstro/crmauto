import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [('identity', '0001_initial')]
    operations = [
        migrations.CreateModel(name='Plan', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('code', models.SlugField(unique=True)),
            ('name', models.CharField(max_length=100)),
            ('price_minor', models.PositiveBigIntegerField()),
            ('max_branches', models.PositiveSmallIntegerField(default=1)),
            ('max_staff', models.PositiveSmallIntegerField(default=5)),
            ('active', models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name='Subscription', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('state', models.CharField(default='trial', max_length=12)),
            ('trial_ends_at', models.DateTimeField(blank=True, null=True)),
            ('paid_through', models.DateTimeField(blank=True, null=True)),
            ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
            ('organization', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='identity.organization')),
            ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='billing.plan')),
        ]),
    ]

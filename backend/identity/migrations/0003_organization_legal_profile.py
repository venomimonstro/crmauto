import uuid
import django.db.models.deletion
from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("identity","0002_staff_invitation")]
    operations=[migrations.CreateModel(name="OrganizationLegalProfile",fields=[
        ("id",models.UUIDField(default=uuid.uuid4,primary_key=True,editable=False,serialize=False)),
        ("legal_name",models.CharField(max_length=250,blank=True)),
        ("entity_kind",models.CharField(max_length=20,default="company",choices=[
            ("company","Юридическое лицо"),("individual","ИП"),("self_employed","Самозанятый")])),
        ("inn",models.CharField(max_length=12,blank=True)),
        ("kpp",models.CharField(max_length=9,blank=True)),
        ("ogrn",models.CharField(max_length=15,blank=True)),
        ("postal_address",models.CharField(max_length=300,blank=True)),
        ("service_address",models.CharField(max_length=300,blank=True)),
        ("phone",models.CharField(max_length=32,blank=True)),
        ("email",models.EmailField(blank=True,max_length=254)),
        ("bank_name",models.CharField(max_length=200,blank=True)),
        ("bik",models.CharField(max_length=9,blank=True)),
        ("account_number",models.CharField(max_length=20,blank=True)),
        ("correspondent_account",models.CharField(max_length=20,blank=True)),
        ("tax_label",models.CharField(max_length=100,blank=True)),
        ("version",models.PositiveIntegerField(default=1)),
        ("organization",models.OneToOneField(to="identity.organization",on_delete=django.db.models.deletion.PROTECT,related_name="legal_profile")),
    ])]

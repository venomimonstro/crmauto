from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("workorders","0004_order_document")]
    operations=[migrations.AlterField(model_name="orderdocument",name="doc_type",
       field=models.CharField(max_length=20,choices=[
         ("work_order","Заказ-наряд"),("intake","Акт приёмки"),
         ("completion","Акт работ (проект)"),("handover","Акт выдачи (проект)"),
         ("warranty","Гарантийная памятка (проект)")]))]

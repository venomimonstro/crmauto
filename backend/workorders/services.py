from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from core.commands import BusinessConflict
from identity.models import AuditEvent
from .models import Estimate, EstimateLine, OrderTransition, WorkOrder

FLOW = {
    "draft": {"awaiting","cancelled"},
    "awaiting": {"approved","draft","cancelled"},
    "approved": {"in_progress","draft","cancelled"},
    "in_progress": {"qa"},
    "qa": {"in_progress","ready"},
    "ready": {"in_progress","delivered"},
}
def total_minor(quantity,price):
    return int((quantity*Decimal(price)).quantize(Decimal("1"),rounding=ROUND_HALF_UP))

def event(order,actor,kind,details=None):
    AuditEvent.objects.create(organization=order.organization,actor=actor,
                              event_type="workorder."+kind,subject_id=order.id,details=details or {})

def change(order,actor,to,reason=""):
    if to not in FLOW.get(order.status,set()):
        raise BusinessConflict("Недопустимый переход заказ-наряда.")
    before=order.status
    order.status=to
    order.version+=1
    order.save(update_fields=["status","version"])
    OrderTransition.objects.create(order=order,actor=actor,previous=before,current=to,reason=reason)
    event(order,actor,"status",{"from":before,"to":to})

def draft(order):
    return Estimate.objects.filter(order=order,state=Estimate.State.DRAFT).first()

def create_revision(order,actor):
    previous=Estimate.objects.filter(order=order).order_by("-revision").first()
    if previous and previous.state==Estimate.State.DRAFT:
        return previous
    revision=Estimate.objects.create(order=order,revision=(previous.revision+1 if previous else 1))
    if previous:
        for line in previous.lines.all():
            EstimateLine.objects.create(estimate=revision,kind=line.kind,title=line.title,
                quantity=line.quantity,unit_price_minor=line.unit_price_minor,total_minor=line.total_minor)
        revision.total_minor=previous.total_minor
        revision.save(update_fields=["total_minor"])
    event(order,actor,"revision_created",{"revision":revision.revision})
    return revision

def recalculate(estimate):
    estimate.total_minor=sum(line.total_minor for line in estimate.lines.all())
    estimate.save(update_fields=["total_minor"])

def transition(order,actor,action,reference="",reason=""):
    if action=="submit":
        estimate=draft(order)
        if order.status!="draft" or not estimate or not estimate.lines.exists():
            raise BusinessConflict("Для согласования нужна смета с позициями в черновике заказа.")
        estimate.state=Estimate.State.SUBMITTED
        estimate.save(update_fields=["state"])
        change(order,actor,"awaiting")
        return
    if action in ("approve","reject"):
        estimate=Estimate.objects.filter(order=order,state="submitted").order_by("-revision").first()
        if order.status!="awaiting" or not estimate:
            raise BusinessConflict("Нет сметы на согласовании.")
        if action=="approve":
            if not reference.strip():
                raise ValidationError({"reference":"Зафиксируйте основание и идентификатор согласования."})
            estimate.state="approved"
            estimate.approved_at=timezone.now()
            estimate.approval_method="recorded_by_employee"
            estimate.approval_reference=reference[:250]
            estimate.save(update_fields=["state","approved_at","approval_method","approval_reference"])
            change(order,actor,"approved")
        else:
            estimate.state="rejected"
            estimate.save(update_fields=["state"])
            change(order,actor,"draft",reason or "Клиент отказался от сметы.")
        return
    if action=="revise":
        if order.status not in ("approved","awaiting","draft","in_progress"):
            raise BusinessConflict("Пересмотр сметы сейчас невозможен.")
        if order.status=="in_progress":
            raise BusinessConflict("Дополнительные работы после начала ремонта требуют отдельного процесса дополнений.")
        if order.status=="awaiting":
            pending=Estimate.objects.filter(order=order,state="submitted").first()
            if pending:
                pending.state="superseded";pending.save(update_fields=["state"])
        create_revision(order,actor)
        if order.status != "draft":
            change(order,actor,"draft","Новая редакция сметы.")
        return
    target={"start":"in_progress","qa":"qa","rework":"in_progress",
            "ready":"ready","deliver":"delivered","cancel":"cancelled"}.get(action)
    if not target:
        raise ValidationError({"action":"Неизвестная операция."})
    if action=="start" and not Estimate.objects.filter(order=order,state="approved").exists():
        raise BusinessConflict("Ремонт запрещён до согласования сметы.")
    if action=="deliver":
        raise BusinessConflict("Выдача заблокирована до реализации финансового и документарного контура S08.")
    if action=="cancel" and order.status!="draft":
        raise BusinessConflict("Отмена после направления сметы требует отдельного документированного процесса.")
    change(order,actor,target,reason)

"""Tenant-scoped, immutable draft print snapshots. These are NOT fiscal receipts or signatures."""
import hashlib
from html import escape
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from core.commands import execute_command, BusinessConflict
from identity.models import Membership
from identity.scope import TenantAPIView, require_roles
from scheduling.views import valid_branch
from .models import WorkOrder, Estimate, OrderDocument

READ=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER,Membership.Roles.VIEWER)
EDIT=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER)
LABELS={"work_order":"Заказ-наряд","intake":"Акт приёмки автомобиля",
        "completion":"Акт выполненных работ (проект)","handover":"Акт выдачи автомобиля (проект)"}
def safe(value):
    return escape(str(value if value is not None else "—"),quote=True)
def cell(label,value):
    return "<tr><th>"+safe(label)+"</th><td>"+safe(value)+"</td></tr>"
def compose(order,kind):
    issued=timezone.localtime()
    customer=order.customer
    vehicle=order.vehicle
    estimate=Estimate.objects.filter(order=order,state="approved").order_by("-revision").first()
    if kind in ("completion","handover") and order.status not in ("qa","ready","delivered"):
        raise BusinessConflict("Документ завершения возможен только после выполнения работ.")
    if kind in ("completion","handover") and (not estimate or order.additional_works.filter(status="proposed").exists()):
        raise BusinessConflict("Для документа завершения нужна согласованная смета и рассмотренные дополнения.")
    try:
        profile=order.organization.legal_profile
    except ObjectDoesNotExist:
        profile=None
    details=[
      cell("Автосервис",order.organization.name),cell("Филиал",order.branch.name),
      cell("Исполнитель",profile.legal_name if profile else "Реквизиты не заполнены"),
      cell("ИНН",profile.inn if profile else "не указан"),
      cell("ОГРН/ОГРНИП",profile.ogrn if profile else "не указан"),
      cell("Адрес исполнителя",profile.service_address if profile else "не указан"),
      cell("Телефон исполнителя",profile.phone if profile else "не указан"),
      cell("Клиент",customer.name),cell("Автомобиль",vehicle.make+" "+vehicle.model),
      cell("VIN",vehicle.vin or "не указан"),cell("Госномер",vehicle.plate or "не указан"),
      cell("Заказ-наряд",str(order.pk)),cell("Дата формирования",issued.strftime("%d.%m.%Y %H:%M")),
      cell("Статус ремонта",order.get_status_display()),cell("Пробег, км",order.odometer_km),
      cell("Причина обращения",order.complaint),cell("Повреждения при приёмке",order.existing_damage),
    ]
    lines=""
    if estimate:
        lines="".join("<tr><td>"+safe(x.title)+"</td><td>"+safe(x.get_kind_display())+"</td><td>"+
                       safe(x.quantity)+"</td><td>"+safe(x.total_minor/100)+" ₽</td></tr>"
                       for x in estimate.lines.order_by("id"))
        details.append(cell("Согласованная редакция сметы",estimate.revision))
        details.append(cell("Сумма по смете",f"{estimate.total_minor / 100:.2f} ₽"))
        details.append(cell("Фиксация согласования",estimate.approval_reference or "Не подтверждено клиентом"))
    if kind=="handover":
        details.append(cell("Выдача автомобиля","Не подтверждена. Документ не удостоверяет фактическую передачу."))
    title=LABELS[kind]
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>'+safe(title)+
      '</title><style>body{font:14px system-ui,Arial,sans-serif;color:#171717;max-width:850px;margin:30px auto;padding:0 20px}'+
      'h1{font-size:24px}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{padding:8px;text-align:left;border:1px solid #ddd;vertical-align:top}th{width:35%;background:#f5f5f5}'+
      '.notice{border:2px solid #444;padding:10px;margin:15px 0;font-weight:bold}'+
      '.sign{display:flex;justify-content:space-between;gap:30px;margin-top:50px}.sign>div{width:45%;border-top:1px solid #666;padding-top:8px}'+
      '@media print{body{margin:0;max-width:none} @page{size:A4;margin:14mm}}</style></head><body>'+
      '<h1>'+safe(title)+'</h1><div class="notice">ПРОЕКТ ДЛЯ ПРОВЕРКИ И ПОДПИСАНИЯ. Не является кассовым чеком, '+ 
      'электронной подписью или доказательством выдачи автомобиля.</div><table>'+
      ''.join(details)+'</table>'+
      ('<h2>Согласованные работы и материалы</h2><table><tr><th>Позиция</th><th>Тип</th><th>Количество</th><th>Сумма</th></tr>'+lines+'</table>' if estimate else '')+
      '<p>Фактические работы, передача автомобиля и законность документа подтверждаются отдельно.</p>'+
      '<div class="sign"><div>Представитель автосервиса / подпись</div><div>Клиент / подпись</div></div>'+
      '</body></html>')

def json_document(doc,include_html=False):
    result={"id":str(doc.pk),"type":doc.doc_type,"title":LABELS[doc.doc_type],
      "revision":doc.revision,"created_at":doc.created_at.isoformat(),"sha256":doc.sha256,
      "state":"unsigned_draft"}
    if include_html:result["html"]=doc.html_snapshot
    return result

class Documents(TenantAPIView):
    def get(self,request,pk):
        require_roles(self.scope,*READ)
        order=get_object_or_404(WorkOrder,pk=pk,organization_id=self.scope.organization_id)
        valid_branch(self.scope,order.branch_id)
        return Response([json_document(d) for d in OrderDocument.objects.filter(order=order).order_by("doc_type","revision")])
    def post(self,request,pk):
        require_roles(self.scope,*EDIT)
        class Payload(serializers.Serializer):
            type=serializers.ChoiceField(choices=list(LABELS))
        serializer=Payload(data=request.data);serializer.is_valid(raise_exception=True)
        kind=serializer.validated_data["type"]
        def create():
            order=get_object_or_404(WorkOrder.objects.select_related("customer","vehicle","organization","branch"),pk=pk,organization_id=self.scope.organization_id)
            valid_branch(self.scope,order.branch_id)
            html=compose(order,kind)
            latest=OrderDocument.objects.filter(order=order,doc_type=kind).order_by("-revision").first()
            doc=OrderDocument.objects.create(organization=order.organization,order=order,
               doc_type=kind,revision=1+(latest.revision if latest else 0),
               html_snapshot=html,sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
               created_by=request.user)
            from identity.models import AuditEvent
            AuditEvent.objects.create(organization=order.organization,actor=request.user,
              event_type="workorder.document.generated",subject_id=doc.pk,
              details={"type":kind,"revision":doc.revision,"sha256":doc.sha256})
            return json_document(doc),201
        result,code=execute_command(request,self.scope,"workorder.document."+str(pk)+"."+kind,create)
        return Response(result,status=code)

class DocumentDetail(TenantAPIView):
    def get(self,request,pk,doc_id):
        require_roles(self.scope,*READ)
        order=get_object_or_404(WorkOrder,pk=pk,organization_id=self.scope.organization_id)
        valid_branch(self.scope,order.branch_id)
        doc=get_object_or_404(OrderDocument,pk=doc_id,order=order,organization_id=self.scope.organization_id)
        return Response(json_document(doc,include_html=True))

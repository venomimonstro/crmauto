from django.utils import timezone
from rest_framework.response import Response
from identity.scope import TenantAPIView
from identity.models import Membership
from rest_framework.exceptions import PermissionDenied
from .models import Plan, Subscription

class Plans(TenantAPIView):
    def get(self, request):
        items=Plan.objects.filter(active=True).order_by('price_minor')
        return Response([{'code':p.code,'name':p.name,'price_minor':p.price_minor,
                          'max_branches':p.max_branches,'max_staff':p.max_staff} for p in items])

class CurrentSubscription(TenantAPIView):
    def get(self, request):
        if self.scope.membership.role not in (Membership.Roles.OWNER,Membership.Roles.MANAGER):
            raise PermissionDenied('Тариф доступен владельцу и управляющему.')
        subscription=Subscription.objects.select_related('plan').filter(
            organization_id=self.scope.organization_id).first()
        if subscription is None:
            return Response({'state':'unconfigured','access':'restricted',
                             'message':'Подписка не настроена. Автоматическая активация отключена.'})
        now=timezone.now()
        # Stored state is not sufficient: an expired active subscription may not grant writes.
        valid_paid=bool(subscription.paid_through and subscription.paid_through>now)
        valid_trial=bool(subscription.state=='trial' and subscription.trial_ends_at and subscription.trial_ends_at>now)
        allowed=(subscription.state=='active' and valid_paid) or valid_trial
        return Response({'state':subscription.state,'access':'write' if allowed else 'read_only',
                         'plan_code':subscription.plan.code,
                         'paid_through':subscription.paid_through,
                         'trial_ends_at':subscription.trial_ends_at,
                         'limits':{'branches':subscription.plan.max_branches,
                                   'staff':subscription.plan.max_staff}})

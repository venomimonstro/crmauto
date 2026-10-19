from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from crm.models import Ownership,Vehicle
from workorders.models import WorkOrder,Estimate
from .models import PortalGrant

class MyPortal(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        grants=PortalGrant.objects.filter(user=request.user,active=True,
            organization__is_active=True,customer__archived_at__isnull=True).select_related('organization','customer')
        results=[]
        for grant in grants[:20]:
            owned_ids=list(Ownership.objects.filter(organization=grant.organization,
                customer=grant.customer,ended_on__isnull=True).values_list('vehicle_id',flat=True))
            vehicles=list(Vehicle.objects.filter(organization=grant.organization,
                id__in=owned_ids).values('id','make','model','year','plate'))
            orders=list(WorkOrder.objects.filter(organization=grant.organization,
                customer=grant.customer).order_by('-created_at').values('id','status','created_at')[:50])
            results.append({'organization_id':str(grant.organization_id),'service':grant.organization.name,
              'customer_id':str(grant.customer_id),'vehicles':vehicles,'orders':orders})
        return Response({'accounts':results,'read_only':True})

class PortalOrder(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,pk):
        valid_grant = PortalGrant.objects.filter(
            user=request.user, active=True,
            organization_id=OuterRef('organization_id'),
            customer_id=OuterRef('customer_id'),
            organization__is_active=True,
            customer__archived_at__isnull=True,
        )
        order=get_object_or_404(WorkOrder.objects.annotate(
            has_valid_grant=Exists(valid_grant)).filter(has_valid_grant=True),pk=pk)
        # A customer can see only submitted or approved versions, never internal draft.
        estimates=Estimate.objects.filter(order=order,state__in=['submitted','approved'])
        return Response({'id':str(order.id),'status':order.status,
          'estimates':[{'revision':x.revision,'state':x.state,'total_minor':x.total_minor} for x in estimates]})

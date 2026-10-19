import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class PortalGrant(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    customer=models.ForeignKey('crm.Customer',on_delete=models.PROTECT)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    active=models.BooleanField(default=False)
    verified_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='portal_grants_verified')
    verification_reference=models.CharField(max_length=250)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['organization','customer','user'],name='portal_grant_unique')]

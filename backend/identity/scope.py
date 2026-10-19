"""Server-validated tenant, role and branch scope for every business API."""
from dataclasses import dataclass
from uuid import UUID

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.views import APIView
from .models import Branch, MemberBranch, Membership


@dataclass(frozen=True)
class Scope:
    membership: Membership
    branch: Branch | None

    @property
    def organization(self):
        return self.membership.organization

    @property
    def organization_id(self):
        return self.membership.organization_id


def resolve_scope(request, require_branch=False):
    raw_org = request.headers.get("X-Organization-ID", "")
    try:
        org_id = UUID(raw_org)
    except (ValueError, AttributeError, TypeError):
        raise ValidationError({"organization": "Выберите организацию."})
    membership = (
        Membership.objects.select_related("organization")
        .filter(user=request.user, organization_id=org_id, is_active=True, organization__is_active=True)
        .first()
    )
    if membership is None:
        # Do not distinguish other tenants from nonexistent tenants.
        raise NotFound("Организация недоступна.")
    raw_branch = request.headers.get("X-Branch-ID", "")
    branch = None
    if raw_branch:
        try:
            branch_id = UUID(raw_branch)
        except (TypeError, ValueError, AttributeError):
            raise ValidationError({"branch": "Некорректный филиал."})
        branch = Branch.objects.filter(
            id=branch_id, organization_id=membership.organization_id, is_active=True
        ).first()
        if not branch:
            raise NotFound("Филиал недоступен.")
        if membership.role not in (Membership.Roles.OWNER, Membership.Roles.MANAGER):
            if not MemberBranch.objects.filter(membership=membership, branch=branch).exists():
                raise PermissionDenied("Нет доступа к филиалу.")
    elif require_branch:
        raise ValidationError({"branch": "Выберите филиал."})
    return Scope(membership=membership, branch=branch)


def require_roles(scope, *roles):
    if scope.membership.role not in roles:
        raise PermissionDenied("Недостаточно прав для операции.")


class TenantAPIView(APIView):
    require_branch = False

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.scope = resolve_scope(request, require_branch=self.require_branch)
        # Enforced centrally: all tenant business POST/PATCH/PUT/DELETE.
        from billing.access import enforce_write_access
        enforce_write_access(request, self.scope.organization_id)

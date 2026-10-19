from django.urls import path
from .policies import ServicePolicies
from .legal import LegalProfile
from .invitations import (StaffInvitations, AcceptStaffInvitation, RevokeStaffInvitation,
                          StaffMembers, DeactivateStaffMember)
from .email_auth import (EmailSignup, EmailVerify, PasswordRecoveryRequest,
                         PasswordRecoveryConfirm, PublicAuthStatus)
from .views import (BranchesView, CsrfView, LoginView, LogoutView, MeView,
                    OrganizationsView, RegisterView)

urlpatterns = [
    path("organization/service-policies",ServicePolicies.as_view()),
    path("organization/legal-profile",LegalProfile.as_view()),
    path("auth/csrf", CsrfView.as_view()),
    path("auth/register", RegisterView.as_view()),
    path("auth/capabilities", PublicAuthStatus.as_view()),
    path("auth/signup-email", EmailSignup.as_view()),
    path("auth/email/verify", EmailVerify.as_view()),
    path("auth/password/recovery", PasswordRecoveryRequest.as_view()),
    path("auth/password/confirm", PasswordRecoveryConfirm.as_view()),
    path("auth/login", LoginView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/me", MeView.as_view()),
    path("organizations", OrganizationsView.as_view()),
    path("branches", BranchesView.as_view()),
    path("staff/invitations", StaffInvitations.as_view()),
    path("staff/invitations/accept", AcceptStaffInvitation.as_view()),
    path("staff/invitations/<uuid:pk>/revoke", RevokeStaffInvitation.as_view()),
    path("staff/members", StaffMembers.as_view()),
    path("staff/members/<uuid:pk>/deactivate", DeactivateStaffMember.as_view()),
]

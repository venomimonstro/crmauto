from django.urls import path
from .views import (BranchesView, CsrfView, LoginView, LogoutView, MeView,
                    OrganizationsView, RegisterView)

urlpatterns = [
    path("auth/csrf", CsrfView.as_view()),
    path("auth/register", RegisterView.as_view()),
    path("auth/login", LoginView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/me", MeView.as_view()),
    path("organizations", OrganizationsView.as_view()),
    path("branches", BranchesView.as_view()),
]

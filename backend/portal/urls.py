from django.urls import path
from .approvals import PortalEstimateDecision
from .views import MyPortal,PortalOrder
urlpatterns=[
    path('portal/orders/<uuid:pk>/estimate-decision',PortalEstimateDecision.as_view()),path('portal/me',MyPortal.as_view()),path('portal/orders/<uuid:pk>',PortalOrder.as_view())]

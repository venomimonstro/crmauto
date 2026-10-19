from django.urls import path
from .views import MyPortal,PortalOrder
urlpatterns=[path('portal/me',MyPortal.as_view()),path('portal/orders/<uuid:pk>',PortalOrder.as_view())]

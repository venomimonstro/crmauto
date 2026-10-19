from django.urls import path
from .views import Suppliers,Purchases,PurchaseDetail,AddLine,PurchaseAction,ReceivePurchase
urlpatterns=[
    path("suppliers",Suppliers.as_view()),
    path("purchases",Purchases.as_view()),
    path("purchases/<uuid:pk>",PurchaseDetail.as_view()),
    path("purchases/<uuid:pk>/lines",AddLine.as_view()),
    path("purchases/<uuid:pk>/actions/<str:action>",PurchaseAction.as_view()),
    path("purchases/<uuid:pk>/receive",ReceivePurchase.as_view()),
]

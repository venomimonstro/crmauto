from django.urls import path
from .views import Cashboxes,Invoices,Payments,Refunds,Movements
urlpatterns=[
    path('cashboxes',Cashboxes.as_view()),
    path('invoices',Invoices.as_view()),
    path('payments',Payments.as_view()),
    path('refunds',Refunds.as_view()),
    path('movements',Movements.as_view()),
]

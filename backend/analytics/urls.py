from django.urls import path
from .views import FinanceSummary,LossCenter
urlpatterns=[
 path("reports/finance",FinanceSummary.as_view()),
 path("reports/losses",LossCenter.as_view()),
]

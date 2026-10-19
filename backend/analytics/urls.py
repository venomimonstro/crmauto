from django.urls import path
from .views import FinanceSummary,LossCenter,DailyOperations
urlpatterns=[
 path("reports/finance",FinanceSummary.as_view()),
 path("reports/losses",LossCenter.as_view()),
 path("reports/daily",DailyOperations.as_view()),
]

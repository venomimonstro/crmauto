from django.urls import path
from .views import Plans, CurrentSubscription
urlpatterns = [
    path("billing/plans", Plans.as_view()),
    path("billing/subscription", CurrentSubscription.as_view()),
]

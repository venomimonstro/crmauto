from django.urls import path
from .views import BaysView, AppointmentsView, AppointmentActions, VisitsView

urlpatterns = [
    path("bays", BaysView.as_view()),
    path("appointments", AppointmentsView.as_view()),
    path("appointments/<uuid:pk>/<str:action>", AppointmentActions.as_view()),
    path("visits", VisitsView.as_view()),
]

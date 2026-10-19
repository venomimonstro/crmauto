from django.urls import path
from .views import Tires,TireRelease,Shifts
urlpatterns=[path('tire-sets',Tires.as_view()),path('tire-sets/<uuid:pk>/release',TireRelease.as_view()),path('staff-shifts',Shifts.as_view())]

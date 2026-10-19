from django.urls import path
from .views import live, ready

urlpatterns = [
    path("health/live", live, name="live"),
    path("health/ready", ready, name="ready"),
]

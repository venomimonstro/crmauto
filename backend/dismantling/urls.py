from django.urls import path
from .views import Donors,Bins,SalvageParts,PartAction
urlpatterns=[
 path('donors',Donors.as_view()),
 path('donor-bins',Bins.as_view()),
 path('salvaged-parts',SalvageParts.as_view()),
 path('salvaged-parts/<uuid:pk>/<str:action>',PartAction.as_view()),
]

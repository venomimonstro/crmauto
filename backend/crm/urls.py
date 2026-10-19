from django.urls import path
from .views import CustomerList, CustomerDetail, VehicleList, VehicleDetail, VehicleTransfer, Search, ImportPreview, ImportApply

urlpatterns = [
    path("customers", CustomerList.as_view()),
    path("customers/<uuid:pk>", CustomerDetail.as_view()),
    path("vehicles", VehicleList.as_view()),
    path("vehicles/<uuid:pk>", VehicleDetail.as_view()),
    path("vehicles/<uuid:pk>/transfer", VehicleTransfer.as_view()),
    path("search", Search.as_view()),
    path("customers/import/preview", ImportPreview.as_view()),
    path("customers/import/apply", ImportApply.as_view()),
]

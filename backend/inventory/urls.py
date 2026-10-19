from django.urls import path
from .views import Warehouses,Parts,Stocks,Receive,Reserve,ReservationAction
urlpatterns=[
    path("warehouses",Warehouses.as_view()),
    path("parts",Parts.as_view()),
    path("stocks",Stocks.as_view()),
    path("stocks/receive",Receive.as_view()),
    path("reservations",Reserve.as_view()),
    path("reservations/<uuid:pk>/<str:action>",ReservationAction.as_view()),
]

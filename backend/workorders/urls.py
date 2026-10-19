from django.urls import path
from .additions import AdditionalWorkList,AdditionalWorkDecision
from .views import Orders,OrderDetail,LineAdd,Actions
urlpatterns=[
    path("workorders",Orders.as_view()),
    path("workorders/<uuid:pk>",OrderDetail.as_view()),
    path("workorders/<uuid:pk>/lines",LineAdd.as_view()),
    path("workorders/<uuid:pk>/actions/<str:action>",Actions.as_view()),
]

from django.urls import path
from .documents import Documents, DocumentDetail
from .tasks import Tasks,TaskAction
from .additions import AdditionalWorkList,AdditionalWorkDecision
from .views import Orders,OrderDetail,LineAdd,Actions
urlpatterns=[
    path('workorders/<uuid:pk>/documents',Documents.as_view()),
    path('workorders/<uuid:pk>/documents/<uuid:doc_id>',DocumentDetail.as_view()),
    path("workorders/<uuid:pk>/tasks",Tasks.as_view()),
    path("workorders/<uuid:pk>/tasks/<uuid:task_id>/<str:action>",TaskAction.as_view()),
    path("workorders/<uuid:pk>/additional-works",AdditionalWorkList.as_view()),
    path("workorders/<uuid:pk>/additional-works/<uuid:work_id>/<str:action>",AdditionalWorkDecision.as_view()),
    path("workorders",Orders.as_view()),
    path("workorders/<uuid:pk>",OrderDetail.as_view()),
    path("workorders/<uuid:pk>/lines",LineAdd.as_view()),
    path("workorders/<uuid:pk>/actions/<str:action>",Actions.as_view()),
]

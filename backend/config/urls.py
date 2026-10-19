from django.urls import include,path
urlpatterns=[
    path("api/v1/",include("core.urls")),
    path("api/v1/",include("identity.urls")),
    path("api/v1/",include("crm.urls")),
    path("api/v1/",include("scheduling.urls")),
    path("api/v1/",include("workorders.urls")),
]

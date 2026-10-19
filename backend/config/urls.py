from django.urls import include,path
urlpatterns=[
    path("api/v1/",include("core.urls")),
    path("api/v1/",include("identity.urls")),
    path("api/v1/",include("crm.urls")),
    path("api/v1/",include("scheduling.urls")),
    path("api/v1/",include("workorders.urls")),
    path("api/v1/",include("inventory.urls")),
    path("api/v1/",include("procurement.urls")),
    path("api/v1/",include("finance.urls")),
    path("api/v1/",include("analytics.urls")),
    path("api/v1/",include("dismantling.urls")),
    path("api/v1/",include("workforce.urls")),
    path("api/v1/",include("billing.urls")),
]

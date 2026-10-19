from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def live(_request):
    return JsonResponse({"status": "ok"})


@require_GET
def ready(_request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})

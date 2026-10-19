import uuid
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data
    messages = detail.get("detail", detail) if isinstance(detail, dict) else detail
    request = context.get("request")
    correlation_id = getattr(request, "correlation_id", str(uuid.uuid4()))
    mapping = {400: "invalid_request", 401: "unauthorized", 403: "forbidden",
               404: "not_found", 405: "method_not_allowed", 409: "state_conflict",
               429: "rate_limited"}
    response.data = {
        "code": mapping.get(response.status_code, "business_rule_failed"),
        "message_ru": str(messages)[:300],
        "field_errors": detail if isinstance(detail, dict) and "detail" not in detail else {},
        "correlation_id": correlation_id,
        "retryable": response.status_code in (429, 503),
    }
    return response

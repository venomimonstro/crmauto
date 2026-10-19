"""CSV import: preview before apply, no implicit cross-tenant merge or partial acceptance."""
import csv
import io
from rest_framework.exceptions import ValidationError
from .models import Customer
from .serializers import CustomerSerializer, digits

MAX_BYTES = 256_000
MAX_ROWS = 200
REQUIRED = {"name", "kind", "phone", "email"}


def parse_csv(text, organization):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES:
        raise ValidationError({"csv": "Ожидается CSV-текст размером до 256 КБ."})
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
        if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
            raise ValidationError({"csv": "Колонки: name,kind,phone,email."})
        if len(reader.fieldnames) > 20:
            raise ValidationError({"csv": "Слишком много колонок."})
        rows = list(reader)
    except (csv.Error, UnicodeError) as exc:
        raise ValidationError({"csv": "Файл CSV повреждён."}) from exc
    if not 1 <= len(rows) <= MAX_ROWS:
        raise ValidationError({"csv": "Одна загрузка: от 1 до 200 строк."})
    result, problems, seen = [], [], set()
    for line, raw in enumerate(rows, start=2):
        data = {key: (raw.get(key) or "").strip() for key in REQUIRED}
        ser = CustomerSerializer(data=data)
        if not ser.is_valid():
            problems.append({"line": line, "fields": ser.errors})
            continue
        # When there is no phone, identical names may represent distinct clients.
        identifier = (data["name"].casefold(), digits(data["phone"])) if digits(data["phone"]) else None
        if identifier and identifier in seen:
            problems.append({"line": line, "fields": {"phone": ["Дубль внутри CSV."]}})
            continue
        if identifier: seen.add(identifier)
        already = bool(identifier and Customer.objects.filter(
            organization=organization,
            name__iexact=data["name"],
            phone_digits=identifier[1],
            archived_at__isnull=True,
        ).exists())
        result.append({"line": line, "action": "skip" if already else "create", "data": data})
    return {
        "entries": result, "errors": problems,
        "create_count": sum(1 for item in result if item["action"] == "create"),
        "skip_count": sum(1 for item in result if item["action"] == "skip"),
    }

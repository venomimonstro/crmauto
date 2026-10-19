import uuid
from django.test import SimpleTestCase
from django.urls import resolve
from workorders.tasks import Tasks, TaskAction
from workorders.additions import AdditionalWorkList, AdditionalWorkDecision

class RepairRouteContracts(SimpleTestCase):
    def test_mechanic_and_additional_work_routes_are_reachable(self):
        order=uuid.uuid4()
        task=uuid.uuid4()
        work=uuid.uuid4()
        expected=[
            (f"/api/v1/workorders/{order}/tasks",Tasks),
            (f"/api/v1/workorders/{order}/tasks/{task}/start",TaskAction),
            (f"/api/v1/workorders/{order}/tasks/{task}/finish",TaskAction),
            (f"/api/v1/workorders/{order}/additional-works",AdditionalWorkList),
            (f"/api/v1/workorders/{order}/additional-works/{work}/decline",AdditionalWorkDecision),
        ]
        for path,view in expected:
            with self.subTest(path=path):
                self.assertIs(resolve(path).func.view_class,view)

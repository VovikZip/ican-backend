"""Administrator-only Excel reports for the shared client workspace."""

from io import BytesIO

import httpx
import pytest
from openpyxl import load_workbook

from app.mongo_runtime.core import ADMIN, MANAGER, current_staff, database
from app.mongo_runtime.main import app
from tests.test_mongo_dropbox_cv import Collection, Database


@pytest.mark.asyncio
async def test_admin_downloads_filtered_client_report_and_manager_is_denied():
    db = Database()
    db.admin_users = Collection([
        {"_id": 1, "email": "admin@example.com", "full_name": "Адміністратор",
         "role": ADMIN, "is_active": True},
        {"_id": 7, "email": "manager@example.com", "full_name": "Консультант",
         "role": MANAGER, "is_active": True},
    ])
    db.mnp_client_request_types = Collection([
        {"_id": "request-1", "name": "Пошук роботи", "is_active": True},
    ])
    db.mnp_employment_stages = Collection([
        {"_id": "result-1", "name": "Проходить співбесіду", "is_active": True},
    ])
    db.mnp_persons = Collection([
        {
            "_id": "person-1", "first_name": "Олена", "last_name": "Тестова",
            "phone": "+380501234567", "email": "olena@example.com", "city": "Харків",
            "status": "case", "workflow_stage": "needs_contact", "needs_contact": True,
            "responsible_staff_id": 7, "client_request_ids": ["request-1"],
            "work_format": "remote", "employment_type": "part_time",
            "employment_stage_id": "result-1", "employment_offer_text": "Добір вакансій",
            "referral_source": "instagram", "tags": [{"name": "Excel"}, {"name": "CRM"}],
            "created_at": "2026-10-01T08:00:00Z", "updated_at": "2026-10-02T09:00:00Z",
        },
        {
            "_id": "person-2", "first_name": "Інший", "status": "active",
            "workflow_stage": "in_progress", "needs_contact": False,
            "created_at": "2026-09-01T08:00:00Z",
        },
    ])
    app.dependency_overrides[database] = lambda: db
    app.dependency_overrides[current_staff] = lambda: {
        "_id": 1, "email": "admin@example.com", "role": ADMIN, "is_active": True,
    }
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/mnp/admin/persons/report.xlsx",
                params={"workflow_stage": "needs_contact", "work_format": "remote"},
            )
            assert response.status_code == 200, response.text
            assert response.headers["content-type"].startswith(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            assert "yellow-hub-clients-" in response.headers["content-disposition"]
            workbook = load_workbook(BytesIO(response.content))
            sheet = workbook["Клієнти"]
            assert sheet["A1"].value == "Yellow Hub · Звіт по клієнтах"
            assert "Клієнтів: 1" in sheet["A2"].value
            headers = [cell.value for cell in sheet[5]]
            row = dict(zip(headers, [cell.value for cell in sheet[6]]))
            assert row["Клієнт"] == "Олена Тестова"
            assert row["Відповідальний консультант"] == "Консультант"
            assert row["Запит клієнта"] == "Пошук роботи"
            assert row["Результат"] == "Проходить співбесіду"
            assert row["Теги для пошуку"] == "Excel; CRM"

            app.dependency_overrides[current_staff] = lambda: {
                "_id": 7, "email": "manager@example.com", "role": MANAGER, "is_active": True,
            }
            forbidden = await client.get("/v1/mnp/admin/persons/report.xlsx")
            assert forbidden.status_code == 403
    finally:
        app.dependency_overrides.pop(database, None)
        app.dependency_overrides.pop(current_staff, None)

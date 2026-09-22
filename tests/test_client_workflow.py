"""Client requests, ownership, next actions and duplicate detection."""

import pytest
from fastapi import HTTPException

from app.mongo_runtime import persons
from app.mongo_runtime.core import ADMIN, MANAGER
from tests.test_mongo_dropbox_cv import Database


@pytest.mark.asyncio
async def test_request_dictionary_and_structured_workflow_round_trip():
    db = Database()
    admin = {"_id": 1, "role": ADMIN}
    manager = {"_id": 7, "role": MANAGER}
    request_type = await persons.create_client_request_type(
        {"name": "  Пошук   роботи  "}, db, admin,
    )

    changed = await persons.update_person_workflow(
        "person-1",
        {
            "client_request_ids": [request_type["id"]],
            "responsible_staff_id": 7,
            "needs_contact": True,
            "next_action_text": "  Передзвонити клієнту  ",
            "next_action_at": "2026-09-23T09:30:00Z",
            "notes": "  Важливий контекст  ",
        },
        db,
        manager,
    )

    assert changed["workflow"]["client_requests"] == [{
        "id": request_type["id"], "name": "Пошук роботи", "is_active": True,
    }]
    assert changed["workflow"]["responsible"]["id"] == 7
    assert changed["workflow"]["needs_contact"] is True
    assert changed["workflow"]["next_action_text"] == "Передзвонити клієнту"
    assert changed["core"]["notes"] == "Важливий контекст"

    removed = await persons.delete_client_request_type(request_type["id"], db, admin)
    assert removed == {"archived": True, "used_by": 1}
    loaded = await persons.get_person("person-1", db, manager)
    assert loaded["workflow"]["client_requests"][0]["is_active"] is False
    assert await persons.list_client_request_types(db, manager) == []


@pytest.mark.asyncio
async def test_workflow_requires_complete_next_action_and_manager_assigns_only_self():
    db = Database()
    await db.admin_users.insert_one({
        "_id": 1, "email": "admin@example.com", "full_name": "Адміністратор",
        "role": ADMIN, "is_active": True,
    })
    manager = {"_id": 7, "role": MANAGER}

    with pytest.raises(HTTPException) as incomplete:
        await persons.update_person_workflow(
            "person-1", {"next_action_text": "Подзвонити"}, db, manager,
        )
    assert incomplete.value.status_code == 422

    with pytest.raises(HTTPException) as reassignment:
        await persons.update_person_workflow(
            "person-1", {"responsible_staff_id": 1}, db, manager,
        )
    assert reassignment.value.status_code == 403


@pytest.mark.asyncio
async def test_phone_normalization_and_duplicate_warning_data():
    db = Database()
    manager = {"_id": 7, "role": MANAGER}
    created = await persons.create_person(
        {"first_name": "Марія", "phone": "050 123-45-67", "email": "MARIA@EXAMPLE.COM"},
        db,
        manager,
    )
    assert created["core"]["phone"] == "+380501234567"
    assert created["core"]["email"] == "maria@example.com"

    matches = await persons.find_person_duplicates(
        phone="+38 (050) 123 45 67", email=None, exclude_person_id=None,
        db=db, staff=manager,
    )
    assert matches == [{
        "id": created["id"], "name": "Марія", "phone": "+380501234567",
        "email": "maria@example.com", "match_reasons": ["phone"], "has_access": True,
    }]

    with pytest.raises(HTTPException) as invalid:
        await persons.create_person({"first_name": "Хибний", "phone": "123"}, db, manager)
    assert invalid.value.status_code == 422


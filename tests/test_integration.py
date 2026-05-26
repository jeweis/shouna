from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.core.config import settings
from app.core.database import Base
from app.main import app
from app.models import Family, FamilyMember, Item, Location, User


def make_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    return TestClient(app)


@pytest.fixture()
def client(tmp_path):
    test_client = make_client(tmp_path)
    yield test_client
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, email: str, family_name: str):
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret123", "family_name": family_name},
    )
    assert register_resp.status_code == 201
    assert register_resp.json()["access_token"]
    assert register_resp.json()["token_type"] == "bearer"

    login_resp = client.post(
        "/api/v1/auth/login/json",
        json={"email": email, "password": "secret123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    families_resp = client.get(
        "/api/v1/auth/me/families",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert families_resp.status_code == 200
    family_id = families_resp.json()[0]["id"]
    return token, family_id


def auth_headers(token: str, family_id: int):
    return {"Authorization": f"Bearer {token}", "X-Family-Id": str(family_id)}


def test_malformed_token_returns_unauthorized(client):
    response = client.get(
        "/api/v1/auth/me/families",
        headers={"Authorization": "Bearer malformed-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "无效凭证，请重新登录"


def test_family_isolation_recursive_delete_search_and_ai_fallback(client):
    token_a, family_a = register_and_login(client, "a@example.com", "A 家")
    token_b, family_b = register_and_login(client, "b@example.com", "B 家")
    headers_a = auth_headers(token_a, family_a)
    headers_b = auth_headers(token_b, family_b)

    forbidden = client.get("/api/v1/locations/tree", headers=auth_headers(token_a, family_b))
    assert forbidden.status_code == 403

    members_resp = client.get("/api/v1/families/current/members", headers=headers_a)
    assert members_resp.status_code == 200
    members = members_resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert members[0]["user"]["email"] == "a@example.com"

    create_family_resp = client.post(
        "/api/v1/families/",
        json={"name": "A 的第二个家"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_family_resp.status_code == 201
    assert create_family_resp.json()["name"] == "A 的第二个家"

    families_resp = client.get(
        "/api/v1/auth/me/families",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert families_resp.status_code == 200
    assert {family["name"] for family in families_resp.json()} == {"A 家", "A 的第二个家"}

    add_member_resp = client.post(
        "/api/v1/families/current/members",
        json={"email": "b@example.com"},
        headers=headers_a,
    )
    assert add_member_resp.status_code == 201
    assert add_member_resp.json()["role"] == "member"

    members_resp = client.get("/api/v1/families/current/members", headers=headers_a)
    assert members_resp.status_code == 200
    assert {member["user"]["email"] for member in members_resp.json()} == {
        "a@example.com",
        "b@example.com",
    }

    root_resp = client.post("/api/v1/locations/", json={"name": "客厅"}, headers=headers_a)
    assert root_resp.status_code == 201
    root_id = root_resp.json()["id"]
    child_resp = client.post(
        "/api/v1/locations/",
        json={"name": "电视柜", "parent_id": root_id},
        headers=headers_a,
    )
    assert child_resp.status_code == 201
    child_payload = child_resp.json()
    child_id = child_payload["id"]
    assert [node["name"] for node in child_payload["location_path"]] == ["客厅", "电视柜"]

    item_resp = client.post(
        "/api/v1/items/",
        json={
            "name": "遥控器",
            "description": "电视遥控器",
            "quantity": 1,
            "tags": ["电器", "客厅"],
            "location_id": child_id,
            "home_location_id": child_id,
        },
        headers=headers_a,
    )
    assert item_resp.status_code == 201
    item_payload = item_resp.json()
    item_id = item_payload["item"]["id"]
    assert item_payload["item"]["name"] == "遥控器"
    assert [node["name"] for node in item_payload["location_path"]] == ["客厅", "电视柜"]

    cross_family_item = client.get(f"/api/v1/items/{item_id}", headers=headers_b)
    assert cross_family_item.status_code == 404

    location_items_resp = client.get(f"/api/v1/locations/{root_id}/items", headers=headers_a)
    assert location_items_resp.status_code == 200
    assert [item["name"] for item in location_items_resp.json()] == ["遥控器"]

    family_items_resp = client.get(
        "/api/v1/items/", headers=auth_headers(token_b, family_a)
    )
    assert family_items_resp.status_code == 200
    assert [item["name"] for item in family_items_resp.json()] == ["遥控器"]

    tree_resp = client.get("/api/v1/locations/tree", headers=headers_a)
    assert tree_resp.status_code == 200
    root_node = tree_resp.json()[0]
    assert root_node["name"] == "客厅"
    assert root_node["item_count"] == 1
    assert root_node["sub_locations"][0]["item_count"] == 1

    search_resp = client.get("/api/v1/search/", params={"q": "遥控"}, headers=headers_a)
    assert search_resp.status_code == 200
    result = search_resp.json()[0]
    assert result["item"]["name"] == "遥控器"
    assert [node["name"] for node in result["location_path"]] == ["客厅", "电视柜"]

    ancestor_search_resp = client.get("/api/v1/search/", params={"q": "客厅"}, headers=headers_a)
    assert ancestor_search_resp.status_code == 200
    ancestor_result = ancestor_search_resp.json()[0]
    assert ancestor_result["item"]["name"] == "遥控器"
    assert [node["name"] for node in ancestor_result["location_path"]] == ["客厅", "电视柜"]

    ai_resp = client.post(
        "/api/v1/items/analyze",
        files={"file": ("item.jpg", b"fake-image", "image/jpeg")},
        headers=headers_a,
    )
    assert ai_resp.status_code == 200
    ai_payload = ai_resp.json()
    assert ai_payload["status"] == "disabled"
    assert ai_payload["result"] == {
        "name": "",
        "description": "",
        "suggested_location": "",
        "tags": [],
        "confidence": 0.0,
    }

    delete_resp = client.delete(f"/api/v1/locations/{root_id}", headers=headers_a)
    assert delete_resp.status_code == 200

    missing_child = client.get(f"/api/v1/locations/{child_id}", headers=headers_a)
    assert missing_child.status_code == 404
    missing_item = client.get(f"/api/v1/items/{item_id}", headers=headers_a)
    assert missing_item.status_code == 404


def test_item_photo_upload_read_delete_and_family_isolation(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_ROOT", str(tmp_path / "uploads"), raising=False)

    token_a, family_a = register_and_login(client, "photo-a@example.com", "照片 A 家")
    token_b, family_b = register_and_login(client, "photo-b@example.com", "照片 B 家")
    headers_a = auth_headers(token_a, family_a)
    headers_b = auth_headers(token_b, family_b)

    location_resp = client.post("/api/v1/locations/", json={"name": "玄关"}, headers=headers_a)
    assert location_resp.status_code == 201
    location_id = location_resp.json()["id"]

    item_resp = client.post(
        "/api/v1/items/",
        json={"name": "钥匙", "quantity": 1, "location_id": location_id},
        headers=headers_a,
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["item"]["id"]

    image_bytes = b"\xff\xd8shouna-test-photo"
    upload_resp = client.post(
        f"/api/v1/items/{item_id}/photos",
        files={"file": ("key.jpg", image_bytes, "image/jpeg")},
        headers=headers_a,
    )
    assert upload_resp.status_code == 201
    photo_payload = upload_resp.json()
    photo_id = photo_payload["id"]
    assert photo_payload["item_id"] == item_id
    assert photo_payload["family_id"] == family_a
    assert photo_payload["storage_provider"] == "local"
    assert photo_payload["storage_key"].startswith(f"items/{family_a}/{item_id}/")
    assert photo_payload["mime_type"] == "image/jpeg"
    assert photo_payload["size_bytes"] == len(image_bytes)

    stored_file = Path(settings.LOCAL_STORAGE_ROOT) / photo_payload["storage_key"]
    assert stored_file.exists()

    content_resp = client.get(f"/api/v1/item-photos/{photo_id}/content", headers=headers_a)
    assert content_resp.status_code == 200
    assert content_resp.headers["content-type"].startswith("image/jpeg")
    assert content_resp.content == image_bytes

    cross_family_upload = client.post(
        f"/api/v1/items/{item_id}/photos",
        files={"file": ("other.jpg", image_bytes, "image/jpeg")},
        headers=headers_b,
    )
    assert cross_family_upload.status_code in {403, 404}

    cross_family_read = client.get(f"/api/v1/item-photos/{photo_id}/content", headers=headers_b)
    assert cross_family_read.status_code in {403, 404}

    non_image_upload = client.post(
        f"/api/v1/items/{item_id}/photos",
        files={"file": ("note.txt", b"not an image", "text/plain")},
        headers=headers_a,
    )
    assert non_image_upload.status_code in {400, 415}

    delete_resp = client.delete(f"/api/v1/items/{item_id}", headers=headers_a)
    assert delete_resp.status_code == 200
    assert not stored_file.exists()

    missing_content = client.get(f"/api/v1/item-photos/{photo_id}/content", headers=headers_a)
    assert missing_content.status_code == 404


def test_item_photo_delete_endpoint_removes_metadata_and_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_ROOT", str(tmp_path / "uploads"), raising=False)

    token, family_id = register_and_login(client, "photo-delete@example.com", "删图家")
    headers = auth_headers(token, family_id)
    location_resp = client.post("/api/v1/locations/", json={"name": "厨房"}, headers=headers)
    assert location_resp.status_code == 201
    item_resp = client.post(
        "/api/v1/items/",
        json={"name": "量杯", "quantity": 1, "location_id": location_resp.json()["id"]},
        headers=headers,
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["item"]["id"]

    upload_resp = client.post(
        f"/api/v1/items/{item_id}/photos",
        files={"file": ("cup.jpg", b"\xff\xd8cup", "image/jpeg")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    photo_payload = upload_resp.json()
    photo_id = photo_payload["id"]
    stored_file = Path(settings.LOCAL_STORAGE_ROOT) / photo_payload["storage_key"]
    assert stored_file.exists()

    delete_resp = client.delete(f"/api/v1/item-photos/{photo_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["id"] == photo_id
    assert not stored_file.exists()

    missing_content = client.get(f"/api/v1/item-photos/{photo_id}/content", headers=headers)
    assert missing_content.status_code == 404


def test_item_photo_upload_idempotency_key_does_not_duplicate(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_ROOT", str(tmp_path / "uploads"), raising=False)

    token, family_id = register_and_login(client, "photo-idem@example.com", "幂等照片家")
    headers = auth_headers(token, family_id)
    headers["Idempotency-Key"] = "upload-photo-idem-001"
    location_resp = client.post("/api/v1/locations/", json={"name": "卧室"}, headers=headers)
    assert location_resp.status_code == 201
    item_resp = client.post(
        "/api/v1/items/",
        json={"name": "眼罩", "quantity": 1, "location_id": location_resp.json()["id"]},
        headers=headers,
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["item"]["id"]

    image_bytes = b"\xff\xd8same-photo"
    first_resp = client.post(
        f"/api/v1/items/{item_id}/photos",
        files={"file": ("mask.jpg", image_bytes, "image/jpeg")},
        headers=headers,
    )
    second_resp = client.post(
        f"/api/v1/items/{item_id}/photos",
        files={"file": ("mask.jpg", image_bytes, "image/jpeg")},
        headers=headers,
    )

    assert first_resp.status_code == 201
    assert second_resp.status_code == 201
    assert second_resp.json()["id"] == first_resp.json()["id"]
    stored_files = list((Path(settings.LOCAL_STORAGE_ROOT) / "items").rglob("*.jpg"))
    assert len(stored_files) == 1


def test_create_item_idempotency_key_does_not_duplicate(client):
    token, family_id = register_and_login(client, "idem@example.com", "幂等家")
    headers = auth_headers(token, family_id)
    headers["Idempotency-Key"] = "create-item-idem-001"

    location_resp = client.post("/api/v1/locations/", json={"name": "书房"}, headers=headers)
    assert location_resp.status_code == 201
    location_id = location_resp.json()["id"]

    payload = {"name": "剪刀", "quantity": 1, "location_id": location_id}
    first_resp = client.post("/api/v1/items/", json=payload, headers=headers)
    second_resp = client.post("/api/v1/items/", json=payload, headers=headers)

    assert first_resp.status_code == 201
    assert second_resp.status_code == 201
    assert second_resp.json()["item"]["id"] == first_resp.json()["item"]["id"]

    items_resp = client.get("/api/v1/items/", headers=headers)
    assert items_resp.status_code == 200
    assert [item["name"] for item in items_resp.json()] == ["剪刀"]


def test_create_location_idempotency_key_does_not_duplicate(client):
    token, family_id = register_and_login(client, "loc-idem@example.com", "空间幂等家")
    headers = auth_headers(token, family_id)
    headers["Idempotency-Key"] = "create-location-idem-001"

    first_resp = client.post("/api/v1/locations/", json={"name": "阳台"}, headers=headers)
    second_resp = client.post("/api/v1/locations/", json={"name": "阳台"}, headers=headers)

    assert first_resp.status_code == 201
    assert second_resp.status_code == 201
    assert second_resp.json()["id"] == first_resp.json()["id"]

    tree_resp = client.get("/api/v1/locations/tree", headers=headers)
    assert tree_resp.status_code == 200
    assert [location["name"] for location in tree_resp.json()] == ["阳台"]


def test_update_item_rejects_stale_offline_version(client):
    token, family_id = register_and_login(client, "conflict@example.com", "冲突家")
    headers = auth_headers(token, family_id)
    location_resp = client.post("/api/v1/locations/", json={"name": "书架"}, headers=headers)
    assert location_resp.status_code == 201
    item_resp = client.post(
        "/api/v1/items/",
        json={"name": "笔记本", "quantity": 1, "location_id": location_resp.json()["id"]},
        headers=headers,
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["item"]["id"]

    stale_headers = {**headers, "If-Unmodified-Since": "2000-01-01T00:00:00"}
    conflict_resp = client.put(
        f"/api/v1/items/{item_id}",
        json={"name": "离线改名"},
        headers=stale_headers,
    )

    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["detail"] == "服务端记录已更新，请先刷新后再保存"

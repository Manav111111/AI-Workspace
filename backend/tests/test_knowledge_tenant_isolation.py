import pytest
from httpx import AsyncClient
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService


@pytest.mark.asyncio
async def test_knowledge_and_vector_tenant_isolation(client: AsyncClient):
    """MANDATORY SECURITY TEST:
    Verifies that Company A can never access, read, upload into, or delete Company B's
    Knowledge Base, Documents, Chunks, or Qdrant vectors.
    """
    # -------------------------------------------------------------------------
    # 1. Setup Tenant A (Alice at Alpha Corp)
    # -------------------------------------------------------------------------
    signup_a = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "alice@alphakb.com",
            "password": "AlphaPassword123!",
            "full_name": "Alice Alpha",
            "company_name": "Alpha Corp",
        },
    )
    assert signup_a.status_code == 201
    data_a = signup_a.json()
    token_a = data_a["token"]["access_token"]
    company_a_id = data_a["company"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Company-ID": company_a_id}

    # Create KB A
    res_kb_a = await client.post(
        "/api/v1/knowledge-bases/",
        json={"name": "Alpha Internal Vault"},
        headers=headers_a,
    )
    assert res_kb_a.status_code == 201
    kb_a_id = res_kb_a.json()["id"]

    # Upload Doc A
    doc_a_content = b"Confidential Alpha Financial Plan: Target revenue is $500M in Q4."
    res_doc_a = await client.post(
        f"/api/v1/knowledge-bases/{kb_a_id}/documents",
        files={"file": ("alpha_plan.txt", doc_a_content, "text/plain")},
        headers=headers_a,
    )
    assert res_doc_a.status_code == 201
    doc_a_id = res_doc_a.json()["id"]

    # -------------------------------------------------------------------------
    # 2. Setup Tenant B (Bob at Beta Corp)
    # -------------------------------------------------------------------------
    signup_b = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "bob@betakb.com",
            "password": "BetaPassword123!",
            "full_name": "Bob Beta",
            "company_name": "Beta Corp",
        },
    )
    assert signup_b.status_code == 201
    data_b = signup_b.json()
    token_b = data_b["token"]["access_token"]
    company_b_id = data_b["company"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Company-ID": company_b_id}

    # Create KB B
    res_kb_b = await client.post(
        "/api/v1/knowledge-bases/",
        json={"name": "Beta Medical Formulary"},
        headers=headers_b,
    )
    assert res_kb_b.status_code == 201
    kb_b_id = res_kb_b.json()["id"]

    # Upload Doc B
    doc_b_content = b"Confidential Beta Medical Patent: Compound X formula and trial results."
    res_doc_b = await client.post(
        f"/api/v1/knowledge-bases/{kb_b_id}/documents",
        files={"file": ("beta_patent.txt", doc_b_content, "text/plain")},
        headers=headers_b,
    )
    assert res_doc_b.status_code == 201
    doc_b_id = res_doc_b.json()["id"]

    # -------------------------------------------------------------------------
    # 3. Legitimate Self-Access Tests
    # -------------------------------------------------------------------------
    get_kb_a = await client.get(f"/api/v1/knowledge-bases/{kb_a_id}", headers=headers_a)
    assert get_kb_a.status_code == 200
    assert get_kb_a.json()["name"] == "Alpha Internal Vault"

    get_doc_a = await client.get(f"/api/v1/documents/{doc_a_id}", headers=headers_a)
    assert get_doc_a.status_code == 200
    assert get_doc_a.json()["filename"] == res_doc_a.json()["filename"]

    # -------------------------------------------------------------------------
    # 4. Cross-Tenant Read & List Isolation Tests
    # -------------------------------------------------------------------------
    # Alice attempts to read Beta's KB
    cross_kb = await client.get(f"/api/v1/knowledge-bases/{kb_b_id}", headers=headers_a)
    assert cross_kb.status_code == 404
    assert cross_kb.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # Alice attempts to read Beta's Document
    cross_doc = await client.get(f"/api/v1/documents/{doc_b_id}", headers=headers_a)
    assert cross_doc.status_code == 404
    assert cross_doc.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # Alice attempts to read Beta's Document Chunks
    cross_chunks = await client.get(f"/api/v1/documents/{doc_b_id}/chunks", headers=headers_a)
    assert cross_chunks.status_code == 404

    # Alice lists documents specifying Beta's KB ID
    cross_list_docs = await client.get(f"/api/v1/knowledge-bases/{kb_b_id}/documents", headers=headers_a)
    assert cross_list_docs.status_code == 404

    # -------------------------------------------------------------------------
    # 5. Cross-Tenant Modification, Upload & Deletion Attacks
    # -------------------------------------------------------------------------
    # Alice attempts to upload a malicious file into Beta's KB
    hack_upload = await client.post(
        f"/api/v1/knowledge-bases/{kb_b_id}/documents",
        files={"file": ("injected.txt", b"Injected data", "text/plain")},
        headers=headers_a,
    )
    assert hack_upload.status_code == 404

    # Alice attempts to delete Beta's document
    hack_delete = await client.delete(f"/api/v1/documents/{doc_b_id}", headers=headers_a)
    assert hack_delete.status_code == 404

    # Alice attempts to spoof X-Company-ID to Beta Corp's ID
    spoofed_headers = {
        "Authorization": f"Bearer {token_a}",
        "X-Company-ID": company_b_id,
    }
    spoof_res = await client.get(f"/api/v1/documents/{doc_b_id}", headers=spoofed_headers)
    assert spoof_res.status_code == 403
    assert spoof_res.json()["error"]["code"] == "FORBIDDEN"

    # -------------------------------------------------------------------------
    # 6. Vector-Layer Tenant Isolation Tests in Qdrant
    # -------------------------------------------------------------------------
    qdrant = QdrantService()
    embedder = EmbeddingService()
    query_vec = embedder.generate_query_embedding("Target revenue financial plan or medical patent")

    # Search as Company A
    results_a = qdrant.search(
        company_id=company_a_id,
        query_vector=query_vec,
        limit=10,
    )
    # Must only contain Company A vectors!
    assert len(results_a) > 0
    for hit in results_a:
        assert hit["payload"]["company_id"] == str(company_a_id)
        assert hit["payload"]["company_id"] != str(company_b_id)
        assert "Alpha" in hit["payload"]["content"]
        assert "Beta" not in hit["payload"]["content"]

    # Search as Company B
    results_b = qdrant.search(
        company_id=company_b_id,
        query_vector=query_vec,
        limit=10,
    )
    # Must only contain Company B vectors!
    assert len(results_b) > 0
    for hit in results_b:
        assert hit["payload"]["company_id"] == str(company_b_id)
        assert hit["payload"]["company_id"] != str(company_a_id)
        assert "Beta" in hit["payload"]["content"]
        assert "Alpha" not in hit["payload"]["content"]

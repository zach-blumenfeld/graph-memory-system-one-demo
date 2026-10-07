"""Thin synchronous REST client for the NAMS routes the SDK does not cover
(workspace database mode, relationships, skills, trace export). Bearer key + X-Workspace-Id on
every call. Secrets are never logged."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from pmm.env import load_dotenv, nams_base_url


class NamsError(RuntimeError):
    def __init__(self, status: int, method: str, path: str, body: Any) -> None:
        self.status, self.method, self.path, self.body = status, method, path, body
        super().__init__(f"NAMS {method} {path} -> {status}: {str(body)[:400]}")


class NamsRest:
    def __init__(self, base: str | None = None, api_key: str | None = None, workspace_id: str | None = None, timeout: float = 90.0, transport: httpx.BaseTransport | None = None) -> None:
        load_dotenv()
        self.base = (base or nams_base_url()).rstrip("/")
        key = api_key or os.environ.get("MEMORY_API_KEY")
        if not key:
            raise RuntimeError("MEMORY_API_KEY is not set")
        self.workspace_id = workspace_id or os.environ.get("MEMORY_WORKSPACE_ID") or ""
        headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
        if self.workspace_id:
            headers["X-Workspace-Id"] = self.workspace_id
        self._c = httpx.Client(base_url=self.base, headers=headers, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._c.close()

    def __enter__(self) -> "NamsRest":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ core
    def request(self, method: str, path: str, *, json: Any = None, params: dict[str, Any] | None = None, raw: bool = False, retries: int = 3) -> Any:
        last: httpx.Response | None = None
        for attempt in range(retries):
            r = self._c.request(method, path, json=json, params=params)
            last = r
            if r.status_code in (429, 502, 503, 504) and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            break
        assert last is not None
        if last.status_code >= 400:
            try:
                body = last.json()
            except ValueError:
                body = last.text
            raise NamsError(last.status_code, method, path, body)
        if raw:
            return last.content
        if last.status_code == 204 or not last.content:
            return None
        try:
            return last.json()
        except ValueError:
            return last.text

    def get(self, path: str, **params: Any) -> Any:
        return self.request("GET", path, params={k: v for k, v in params.items() if v is not None} or None)

    def post(self, path: str, json: Any = None) -> Any:
        return self.request("POST", path, json=json)

    def put(self, path: str, json: Any = None) -> Any:
        return self.request("PUT", path, json=json)

    # ------------------------------------------------------------------ system / workspace
    def version(self) -> dict[str, Any]:
        return self.get("/v1/version")

    def workspace(self) -> dict[str, Any]:
        return self.get("/v1/workspace")

    def database(self) -> dict[str, Any]:
        return self.get("/v1/workspace/database")

    def test_connection(self, uri: str, username: str, password: str, database: str = "neo4j") -> dict[str, Any]:
        return self.post("/v1/workspace/database/test", {"uri": uri, "username": username, "password": password, "database": database})

    def set_database_external(self, uri: str, username: str, password: str, database: str = "neo4j") -> dict[str, Any]:
        return self.put("/v1/workspace/database", {"mode": "external", "connection": {"uri": uri, "username": username, "password": password, "database": database}})

    def wait_for_workspace(self, timeout: float = 600.0, interval: float = 5.0, on_poll: Any = None) -> dict[str, Any]:
        deadline = time.time() + timeout
        ws = self.workspace()
        while ws.get("status") != "active" and time.time() < deadline:
            if on_poll:
                on_poll(ws)
            time.sleep(interval)
            ws = self.workspace()
        return ws

    # ------------------------------------------------------------------ conversations / messages
    def create_conversation(self, metadata: dict[str, str] | None = None, user_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if metadata:
            body["metadata"] = {k: str(v) for k, v in metadata.items()}
        if user_id:
            body["userId"] = user_id
        return self.post("/v1/conversations", body)

    def list_conversations(self, limit: int = 100) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page = self.get("/v1/conversations", limit=limit, cursor=cursor)
            out.extend(page.get("conversations", []))
            cursor = page.get("next_cursor") or None
            if not cursor:
                return out

    def conversation(self, cid: str) -> dict[str, Any]:
        return self.get(f"/v1/conversations/{cid}")

    def messages(self, cid: str, limit: int = 200) -> list[dict[str, Any]]:
        page = self.get(f"/v1/conversations/{cid}/messages", limit=limit)
        return page.get("messages", page) if isinstance(page, dict) else page

    def add_message(self, cid: str, role: str, content: str, metadata: dict[str, str] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"role": role, "content": content}
        if metadata:
            body["metadata"] = metadata
        return self.post(f"/v1/conversations/{cid}/messages", body)

    def bulk_messages(self, cid: str, messages: list[dict[str, Any]]) -> Any:
        return self.post(f"/v1/conversations/{cid}/messages/bulk", {"messages": messages})

    def delete_conversation(self, cid: str) -> Any:
        return self.request("DELETE", f"/v1/conversations/{cid}")

    # ------------------------------------------------------------------ reasoning
    def record_step(self, conversation_id: str, reasoning: str, action_taken: str, result: str | None = None) -> dict[str, Any]:
        body = {"conversationId": conversation_id, "reasoning": reasoning, "actionTaken": action_taken}
        if result is not None:
            body["result"] = result
        return self.post("/v1/reasoning/steps", body)

    def record_tool_call(self, tool_name: str, input_json: str, step_id: str | None, status: str = "success", output_json: str | None = None, duration_ms: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"toolName": tool_name, "input": input_json, "status": status}
        if step_id:
            body["stepId"] = step_id
        if output_json is not None:
            body["output"] = output_json
        if duration_ms is not None:
            body["durationMs"] = int(duration_ms)
        return self.post("/v1/reasoning/tool-calls", body)

    def trace(self, conversation_id: str) -> dict[str, Any]:
        return self.get(f"/v1/reasoning/trace/{conversation_id}")

    # ------------------------------------------------------------------ entities / relationships
    def bulk_entities(self, entities: list[dict[str, Any]]) -> Any:
        return self.post("/v1/entities/bulk", {"entities": entities})

    def create_entity(self, name: str, type_: str, description: str | None = None, properties: dict[str, str] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "type": type_}
        if description:
            body["description"] = description
        if properties:
            body["properties"] = {k: str(v) for k, v in properties.items() if v is not None}
        return self.post("/v1/entities", body)

    def entity(self, entity_id: str) -> dict[str, Any]:
        return self.get(f"/v1/entities/{entity_id}")

    def entities(self, type_: str | None = None, limit: int = 200) -> Any:
        return self.get("/v1/entities", type=type_, limit=limit)

    def bulk_relationships(self, relationships: list[dict[str, Any]]) -> Any:
        return self.post("/v1/relationships/bulk", {"relationships": relationships})

    def create_relationship(self, source_id: str, target_id: str, rel_type: str, properties: dict[str, Any] | None = None, confidence: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"sourceId": source_id, "targetId": target_id, "relationshipType": rel_type}
        if properties:
            body["properties"] = properties
        if confidence is not None:
            body["confidence"] = confidence
        return self.post("/v1/relationships", body)

    # ------------------------------------------------------------------ query
    def cypher(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        out = self.post("/v1/query", {"cypher": query, "params": params or {}})
        if isinstance(out, dict):
            for key in ("results", "rows", "records", "data"):
                if key in out and isinstance(out[key], list):
                    return out[key]
        return out if isinstance(out, list) else []

    # ------------------------------------------------------------------ ontology
    def ontologies(self) -> list[dict[str, Any]]:
        return self.get("/v1/ontologies").get("ontologies", [])

    def active_ontology(self) -> dict[str, Any]:
        return self.get("/v1/ontologies/active")

    def create_ontology(self, ontology: dict[str, Any], validation_mode: str = "permissive", message: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"ontology": ontology, "validation_mode": validation_mode}
        if message:
            body["message"] = message
        return self.post("/v1/ontologies", body)

    def ontology(self, ontology_id: str) -> dict[str, Any]:
        return self.get(f"/v1/ontologies/{ontology_id}")

    def activate_ontology(self, version_id: str) -> dict[str, Any]:
        return self.post("/v1/ontologies/active", {"version_id": version_id})

    # ------------------------------------------------------------------ skills
    def skill_capabilities(self) -> dict[str, Any]:
        return self.get("/v1/skills/capabilities")

    def skill_generate(self, scope: dict[str, Any], name_hint: str | None = None, procedure_format: str = "graph", skill_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"scope": scope, "procedureFormat": procedure_format}
        if name_hint:
            body["nameHint"] = name_hint
        if skill_id:
            body["skillId"] = skill_id
        return self.post("/v1/skills/generate", body)

    def skill_run(self, run_id: str) -> dict[str, Any]:
        return self.get(f"/v1/skills/runs/{run_id}")

    def skill_runs(self) -> Any:
        return self.get("/v1/skills/runs")

    def skills(self) -> Any:
        return self.get("/v1/skills")

    def skill(self, skill_id: str) -> dict[str, Any]:
        return self.get(f"/v1/skills/{skill_id}")

    def skill_review(self, skill_id: str, decision: str = "approve", feedback: str | None = None) -> Any:
        body: dict[str, Any] = {"decision": decision}
        if feedback:
            body["feedback"] = feedback
        return self.post(f"/v1/skills/{skill_id}/review", body)

    def skill_publish(self, skill_id: str) -> Any:
        return self.post(f"/v1/skills/{skill_id}/publish")

    def skill_download(self, skill_id: str, version: str | None = None) -> bytes:
        return self.request("GET", f"/v1/skills/{skill_id}/download", params={"version": version} if version else None, raw=True)

    def skill_explain_provenance(self, skill_id: str) -> Any:
        return self.get(f"/v1/skills/{skill_id}/explain-provenance")

    def skill_drift(self, skill_id: str) -> Any:
        return self.get(f"/v1/skills/{skill_id}/drift")

    def skill_governance(self) -> Any:
        return self.get("/v1/skills/governance")

"""One place that builds the neo4j-agent-memory client (bolt backend, no embeddings, no extraction)
and a plain driver for the typed domain edges and read queries."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager, contextmanager

from blast.env import require


def settings():
    from neo4j_agent_memory import MemorySettings

    env = require("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    return MemorySettings(
        neo4j={"uri": env["NEO4J_URI"], "username": env["NEO4J_USERNAME"], "password": env["NEO4J_PASSWORD"], "database": os.environ.get("NEO4J_DATABASE", "neo4j")},
        # No embedding provider is called: every write passes generate_embedding=False. The key is a placeholder the SDK requires.
        embedding={"provider": "openai", "api_key": os.environ.get("OPENAI_API_KEY", "not-used")},
        extraction={"enable_spacy": False, "enable_gliner": False, "enable_llm_fallback": False},
    )


@asynccontextmanager
async def client():
    from neo4j_agent_memory import MemoryClient

    async with MemoryClient(settings()) as m:
        yield m


@contextmanager
def driver():
    from neo4j import GraphDatabase

    env = require("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    with GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USERNAME"], env["NEO4J_PASSWORD"]), notifications_min_severity="OFF") as d:
        yield d


def cypher(query: str, **params):
    with driver() as d:
        return [r.data() for r in d.execute_query(query, database_=os.environ.get("NEO4J_DATABASE", "neo4j"), **params).records]

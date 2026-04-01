"""DiagDocu Agent – GitHub Copilot Extension server.

This FastAPI application implements the GitHub Copilot Extension protocol.
When a user selects the *DiagDocu* agent in Copilot Chat and sends a message
such as::

    Erstelle die DiagDocu für DFC_rbe_CddUTnet_UTnet1Plaus

the server:

1. Extracts the DFC identifier from the message.
2. If a ``SOURCE_ROOT`` environment variable points to a source directory,
   parses the C/H and A2L files found there.
3. Generates a Markdown DiagDocu document.
4. Streams the result back to Copilot Chat using Server-Sent Events (SSE)
   in the OpenAI streaming format.

When ``COPILOT_TOKEN`` is available the generation is forwarded to the GitHub
Copilot LLM API so the model can enrich the documentation.  Without a token
the agent falls back to the built-in template generator.

Environment variables
---------------------
SOURCE_ROOT
    Optional path to the directory that contains C, H, and A2L source files.
    Defaults to the current working directory.
PORT
    TCP port to listen on.  Defaults to ``8080``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from .diagdocu import extract_dfc_name, generate_diagdocu

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COPILOT_API_URL = "https://api.githubcopilot.com/chat/completions"

SYSTEM_PROMPT = """\
Du bist der DiagDocu-Agent, ein spezialisierter Assistent für die Erstellung
von Diagnose-Dokumentationen (DiagDocu) für eingebettete Automotive-Software.

Wenn du gebeten wirst, eine DiagDocu für eine DFC-Funktion zu erstellen,
analysierst du den bereitgestellten Quellcode (C- und H-Dateien) sowie die
A2L-Kalibrierungsdatei und erstellst eine strukturierte Markdown-Dokumentation.

Die DiagDocu soll folgende Abschnitte enthalten:
1. **Übersicht** – Kurze Beschreibung der DFC-Funktion und ihres Zwecks
2. **Eingangsgrößen** – Signale und Parameter, die die DFC-Funktion liest
3. **Fehlerbedingungen** – Bedingungen, unter denen ein Fehler erkannt wird
4. **Fehlerspeicherung** – Wie und wann der Fehler gespeichert wird
5. **Kalibrierparameter** – Relevante Kalibrierparameter aus der A2L-Datei
6. **Quellcode-Referenzen** – Relevante Dateien und Funktionen

Antworte auf Deutsch, es sei denn, der Benutzer fragt auf Englisch.
"""

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DiagDocu Agent",
    description=(
        "GitHub Copilot Extension that generates diagnostic documentation "
        "(DiagDocu) from C/H source files and A2L calibration files."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def health_check() -> dict:
    """Health-check / discovery endpoint."""
    return {"status": "ok", "agent": "DiagDocu"}


@app.post("/")
async def handle_copilot_chat(request: Request) -> StreamingResponse:
    """Handle GitHub Copilot Extension chat requests.

    Receives the conversation history, generates a DiagDocu for the requested
    DFC, and streams the Markdown result back as SSE.
    """
    body = await request.json()

    # The GitHub Copilot token – used both to authenticate with the Copilot
    # LLM API and (optionally) to call the GitHub REST API.
    copilot_token: str = request.headers.get("X-GitHub-Token", "")

    messages: list[dict] = body.get("messages", [])
    last_message = _get_last_user_message(messages)
    dfc_name = extract_dfc_name(last_message)

    source_root_env = os.environ.get("SOURCE_ROOT")
    source_root = Path(source_root_env) if source_root_env else None

    return StreamingResponse(
        _stream(dfc_name, messages, copilot_token, source_root),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------


async def _stream(
    dfc_name: str | None,
    messages: list[dict],
    copilot_token: str,
    source_root: Path | None,
) -> AsyncIterator[str]:
    """Yield SSE data lines for the full response."""
    if not dfc_name:
        yield _sse_chunk(
            "Bitte gib einen DFC-Namen an, z.\u202fB.:\n\n"
            "`Erstelle die DiagDocu für DFC_rbe_CddUTnet_UTnet1Plaus`",
            finish_reason="stop",
        )
        yield "data: [DONE]\n\n"
        return

    # 1. Try to generate from local source files
    doc = generate_diagdocu(dfc_name, source_root)

    # 2. If a Copilot token is available, enrich the document via the LLM
    if copilot_token:
        augmented = _build_llm_messages(dfc_name, messages, doc)
        async for sse_line in _call_copilot_api(augmented, copilot_token):
            yield sse_line
        return

    # 3. Fall back: stream the template document we generated locally
    chunk_size = 120
    for i in range(0, len(doc), chunk_size):
        yield _sse_chunk(doc[i : i + chunk_size])
        await asyncio.sleep(0.01)

    yield _sse_chunk("", finish_reason="stop")
    yield "data: [DONE]\n\n"


def _build_llm_messages(
    dfc_name: str,
    original_messages: list[dict],
    template_doc: str,
) -> list[dict]:
    """Construct the message list for the Copilot LLM API call."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *original_messages,
        {
            "role": "user",
            "content": (
                f"Bitte erstelle eine vollständige DiagDocu für `{dfc_name}`.\n\n"
                "Hier ist ein vorbereitetes Template (aus lokalem Quellcode-Parsing):\n\n"
                f"{template_doc}\n\n"
                "Ergänze und verbessere das Template soweit möglich."
            ),
        },
    ]


async def _call_copilot_api(
    messages: list[dict],
    token: str,
) -> AsyncIterator[str]:
    """Forward *messages* to the GitHub Copilot LLM API and relay SSE lines."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Copilot-Integration-Id": "diagdocu-agent",
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST", COPILOT_API_URL, headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line + "\n\n"
                        if line.strip() == "data: [DONE]":
                            return
    except httpx.HTTPError as exc:
        logger.error("Copilot API error: %s", exc)
        yield _sse_chunk(
            "\n\n*Fehler beim Abrufen der Copilot-API – lokales Template verwendet.*",
            finish_reason="stop",
        )
        yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _get_last_user_message(messages: list[dict]) -> str:
    """Return the text content of the most recent ``user`` message."""
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block.get("text", "")
    return ""


def _sse_chunk(content: str, *, finish_reason: str | None = None) -> str:
    """Encode *content* as an SSE data line in the OpenAI streaming format."""
    payload: dict = {
        "id": "chatcmpl-diagdocu",
        "object": "chat.completion.chunk",
        "model": "diagdocu",
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload)}\n\n"

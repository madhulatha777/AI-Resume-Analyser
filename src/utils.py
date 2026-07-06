"""Shared utilities for the AI Resume Analyzer.

Purpose
-------
This module is the foundation that every other ``src`` module depends on. It
provides:

* Application configuration loaded from environment variables / ``.env``.
* A reusable, lazily-cached Groq LLM client (``get_llm``).
* A robust JSON extraction helper that tolerates the small formatting quirks
  LLMs sometimes produce (markdown fences, leading prose, trailing commas).
* A generic ``run_structured_chain`` helper that runs a LangChain prompt,
  parses the JSON response, and validates it against a Pydantic model.
* Project-wide custom exceptions and a configured logger.

Connections
-----------
``analyzer.py``, ``matcher.py``, ``ats.py`` and ``interview.py`` all build a
``ChatPromptTemplate`` (from ``prompts.py``) and hand it to
``run_structured_chain`` together with the Pydantic schema they expect back.
``app.py`` calls ``get_settings`` / ``get_llm`` to wire everything together.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

# Load variables from a local .env file as early as possible.
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ai_resume_analyzer")

T = TypeVar("T", bound=BaseModel)


# --------------------------------------------------------------------------- #
# Custom exceptions
# --------------------------------------------------------------------------- #
class ResumeAnalyzerError(Exception):
    """Base error for all application-specific failures."""


class MissingAPIKeyError(ResumeAnalyzerError):
    """Raised when the Groq API key is not configured."""


class PDFParsingError(ResumeAnalyzerError):
    """Raised when a PDF cannot be read or contains no extractable text."""


class LLMResponseError(ResumeAnalyzerError):
    """Raised when the LLM response cannot be parsed/validated."""


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Settings:
    """Immutable application settings sourced from the environment."""

    groq_api_key: str
    model: str
    temperature: float
    max_retries: int
    request_timeout: int

    @property
    def has_api_key(self) -> bool:
        """Return ``True`` only when a real-looking key is present."""
        key = (self.groq_api_key or "").strip()
        return bool(key) and key != "your_groq_api_key_here"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build (and cache) the :class:`Settings` object from the environment."""

    def _float(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, default))
        except (TypeError, ValueError):
            return default

    def _int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, default))
        except (TypeError, ValueError):
            return default

    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=_float("GROQ_TEMPERATURE", 0.2),
        max_retries=_int("GROQ_MAX_RETRIES", 2),
        request_timeout=_int("GROQ_REQUEST_TIMEOUT", 60),
    )


# --------------------------------------------------------------------------- #
# LLM client
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def get_llm():
    """Return a cached ``ChatGroq`` client.

    The import is performed lazily so that lightweight consumers (e.g. the
    PDF parser or the unit tests) do not pay the import cost or require the
    API key just to use unrelated helpers.

    Raises
    ------
    MissingAPIKeyError
        If ``GROQ_API_KEY`` is not set to a real value.
    """

    settings = get_settings()
    if not settings.has_api_key:
        raise MissingAPIKeyError(
            "GROQ_API_KEY is not set. Create a .env file (see .env.example) "
            "and add your key from https://console.groq.com/keys"
        )

    # Imported here to keep module import side-effect free and fast.
    from langchain_groq import ChatGroq

    logger.info("Initializing ChatGroq client with model=%s", settings.model)
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.model,
        temperature=settings.temperature,
        max_retries=settings.max_retries,
        timeout=settings.request_timeout,
    )


# --------------------------------------------------------------------------- #
# JSON parsing helpers
# --------------------------------------------------------------------------- #
def extract_json(text: str) -> dict:
    """Extract and parse the first JSON object found in ``text``.

    LLMs occasionally wrap JSON in markdown fences or prepend a sentence of
    explanation despite instructions. This helper strips common artifacts and
    falls back to locating the outermost ``{...}`` block.

    Raises
    ------
    LLMResponseError
        If no valid JSON object can be recovered.
    """

    if not text or not text.strip():
        raise LLMResponseError("LLM returned an empty response.")

    cleaned = text.strip()

    # Remove ```json ... ``` or ``` ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()

    # Fast path: the whole string is valid JSON.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: grab the outermost brace-delimited block.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        # Remove trailing commas that break strict JSON parsing.
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"Could not parse JSON from LLM response: {exc}"
            ) from exc

    raise LLMResponseError("No JSON object found in the LLM response.")


def run_structured_chain(prompt, schema: Type[T], variables: dict, llm=None) -> T:
    """Run a prompt → LLM → JSON → Pydantic pipeline and return the model.

    Parameters
    ----------
    prompt:
        A LangChain ``ChatPromptTemplate`` (or any runnable that accepts the
        provided ``variables`` and produces a chat message).
    schema:
        The Pydantic model class used to validate the parsed JSON.
    variables:
        Mapping of prompt input variables.
    llm:
        Optional pre-built LLM. When omitted, :func:`get_llm` is used. Passing
        an explicit client makes the function trivial to unit test with a fake.

    Raises
    ------
    LLMResponseError
        If the response cannot be parsed or fails schema validation.
    """

    from langchain_core.output_parsers import StrOutputParser

    client = llm or get_llm()
    chain = prompt | client | StrOutputParser()

    try:
        raw = chain.invoke(variables)
    except ResumeAnalyzerError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a friendly message.
        logger.exception("LLM invocation failed")
        raise LLMResponseError(f"The language model request failed: {exc}") from exc

    data = extract_json(raw)
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        logger.error("Schema validation failed for %s: %s", schema.__name__, exc)
        raise LLMResponseError(
            f"The model response did not match the expected format: {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Misc helpers
# --------------------------------------------------------------------------- #
def clamp_score(value: object, low: int = 0, high: int = 100) -> int:
    """Coerce ``value`` to an int and clamp it into the ``[low, high]`` range."""

    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return low
    return max(low, min(high, score))


def truncate(text: str, max_chars: int = 12000) -> str:
    """Truncate very long text to keep prompts within sensible token limits."""

    if text and len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated]..."
    return text

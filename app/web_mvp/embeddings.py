"""Embedding abstraction for RAG pipeline."""

from __future__ import annotations

import logging
import hashlib
from typing import Literal

logger = logging.getLogger(__name__)

import os
from google import genai
from google.genai.errors import APIError


# Configurable constants
EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIMENSION = 768

class LocalFallbackEmbeddingProvider:
    """Fallback embedding provider that uses standard library hashing to create a vector.
    WARNING: This is NOT a real semantic embedding. It is a fallback for offline dev/testing."""
    @staticmethod
    def get_embedding(text: str, dim: int = EMBEDDING_DIMENSION) -> list[float]:
        vec = [0.0] * dim
        words = text.casefold().split()
        stop_words = {"the", "and", "for", "are", "with", "about", "what", "how", "who", "where", "when", "exact", "tell", "show"}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
                vec[idx] += 1.0
        
        magnitude = sum(x*x for x in vec) ** 0.5
        if magnitude > 0:
            return [x / magnitude for x in vec]
        return vec

class HostedEmbeddingProvider:
    """Hosted semantic embedding provider using Google GenAI."""
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
    async def get_embedding(self, text: str) -> list[float] | None:
        if not self.client:
            logger.warning("GEMINI_API_KEY is not set. Cannot use HostedEmbeddingProvider.")
            return None
            
        try:
            # We use synchronous embed call but wrapped if needed, or run in executor.
            # For this MVP, calling it directly since google-genai client handles retries
            response = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text
            )
            return response.embeddings[0].values
        except APIError as e:
            logger.error(f"Hosted Embedding API Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate hosted embedding: {e}")
            return None

class EmbeddingProvider:
    _hosted_provider = HostedEmbeddingProvider()
    
    @classmethod
    async def get_embedding(cls, text: str) -> list[float]:
        """Get embedding using Hosted provider, fallback to Local if unavailable."""
        hosted_vec = await cls._hosted_provider.get_embedding(text)
        if hosted_vec:
            return hosted_vec
            
        logger.warning("Falling back to LocalFallbackEmbeddingProvider for RAG.")
        return LocalFallbackEmbeddingProvider.get_embedding(text)

async def get_embedding(text: str) -> list[float] | None:
    """Generate embedding for the given text using the configured provider."""
    return await EmbeddingProvider.get_embedding(text)

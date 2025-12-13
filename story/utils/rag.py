import os
import logging
import json
import random
import math
import hashlib
import numpy as np

from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from google import genai

# ------------------------------------------
# Setup Logging
# ------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ------------------------------------------
# Load env variables
# ------------------------------------------
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

# ------------------------------------------
# Initialize Client
# ------------------------------------------
client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        logging.error(f"Failed to init Gemini Client: {e}")

# ==========================================
# RAG ENGINE
# ==========================================
class RAG_Engine:
    EMBEDDING_MODEL = "text-embedding-004"
    DIFFICULTY_BOOST = 0.05  # Soft preference, not a hard filter

    def __init__(
        self,
        data_path=os.path.join(os.path.dirname(__file__), "data", "stories.json"),
        embeddings_path=os.path.join(os.path.dirname(__file__), "data", "embeddings.json"),
    ):
        self.data_path = data_path
        self.embeddings_path = embeddings_path

        self.examples = []
        self.embeddings = {}  # {hash: embedding}

        self.load_data()
        self._load_embeddings_from_disk()

    # --------------------------------------
    # Data Loading
    # --------------------------------------
    def load_data(self):
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, "r", encoding="utf-8") as f:
                    self.examples = json.load(f)
                logging.info(f"Loaded {len(self.examples)} examples.")
            else:
                logging.warning("Story data file not found.")
        except Exception as e:
            logging.error(f"Failed to load story data: {e}")

    # --------------------------------------
    # Embedding Utilities
    # --------------------------------------
    def _example_text(self, ex: dict) -> str:
        """
        Canonical text used for embeddings.
        Query text MUST match this structure.
        """
        return (
            f"Story topic: {ex.get('topic', '')}. "
            f"Genre and difficulty: {ex.get('difficulty', '')}. "
            f"Premise: {ex.get('short_story', '')}"
        )

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _get_embedding(self, text: str, client) -> list:
        try:
            result = client.models.embed_content(
                model=self.EMBEDDING_MODEL,
                contents=text,
            )
            return result.embeddings[0].values
        except Exception as e:
            logging.warning(f"Embedding failed: {e}")
            return []

    # --------------------------------------
    # Embedding Cache
    # --------------------------------------
    def _load_embeddings_from_disk(self):
        if not os.path.exists(self.embeddings_path):
            return
        try:
            with open(self.embeddings_path, "r", encoding="utf-8") as f:
                self.embeddings = json.load(f)
            logging.info(f"Loaded {len(self.embeddings)} cached embeddings.")
        except Exception as e:
            logging.warning(f"Failed to load embeddings cache: {e}")

    def _save_embeddings_to_disk(self):
        try:
            with open(self.embeddings_path, "w", encoding="utf-8") as f:
                json.dump(self.embeddings, f)
        except Exception as e:
            logging.error(f"Failed to save embeddings cache: {e}")

    def _ensure_embeddings(self, client):
        updated = False

        for ex in self.examples:
            text = self._example_text(ex)
            text_hash = self._hash_text(text)

            if text_hash not in self.embeddings:
                emb = self._get_embedding(text, client)
                if emb:
                    self.embeddings[text_hash] = emb
                    updated = True

        if updated:
            self._save_embeddings_to_disk()

    # --------------------------------------
    # Similarity
    # --------------------------------------
    # Manual cosine similarity implementation (commented out in favor of sklearn)
    # def _cosine_similarity(self, a: list, b: list) -> float:
    #     if not a or not b:
    #         return 0.0
    #     dot = sum(x * y for x, y in zip(a, b))
    #     norm_a = math.sqrt(sum(x * x for x in a))
    #     norm_b = math.sqrt(sum(y * y for y in b))
    #     if norm_a == 0 or norm_b == 0:
    #         return 0.0
    #     return dot / (norm_a * norm_b)

    def _cosine_similarity(self, a: list, b: list) -> float:
        if not a or not b:
            return 0.0

        a = np.array(a).reshape(1, -1)
        b = np.array(b).reshape(1, -1)

        return float(cosine_similarity(a, b)[0][0])

    # --------------------------------------
    # Public API
    # --------------------------------------
    def get_examples(
        self,
        user_prompt: str,
        target_difficulty: str,
        client=None,
        k: int = 3,
    ) -> str:
        if not self.examples:
            return ""

        if client:
            self._ensure_embeddings(client)

        # Build query text aligned with example embeddings
        query_text = (
            f"Story idea: {user_prompt}. "
            f"Intended difficulty: {target_difficulty}. "
            f"This is a narrative premise."
        )

        query_vec = self._get_embedding(query_text, client) if client else []

        scored = []

        for ex in self.examples:
            text = self._example_text(ex)
            text_hash = self._hash_text(text)
            emb = self.embeddings.get(text_hash)

            score = 0.0
            if query_vec and emb:
                score = self._cosine_similarity(query_vec, emb)

            # Soft difficulty boost
            if ex.get("difficulty", "").lower() == target_difficulty.lower():
                score += self.DIFFICULTY_BOOST

            scored.append((score, ex))

        # Sort by relevance
        scored.sort(key=lambda x: x[0], reverse=True)

        # Fallback if embeddings failed
        if not any(score > 0 for score, _ in scored):
            selected = random.sample(self.examples, min(k, len(self.examples)))
        else:
            selected = [ex for _, ex in scored[:k]]

        # ----------------------------------
        # Format Output (Inspirational Only)
        # ----------------------------------
        output = ""
        for i, ex in enumerate(selected, 1):
            output += f"\nExample {i}:\n"
            output += f"Topic: {ex.get('topic', 'Unknown')}\n"
            output += f"Difficulty: {ex.get('difficulty', 'Unknown')}\n"
            output += f"Premise: {ex.get('short_story', '')}\n"

        return output


# ------------------------------------------
# Manual Test
# ------------------------------------------
if __name__ == "__main__":
    engine = RAG_Engine()
    examples = engine.get_examples(
        user_prompt="A fairy tale about a cursed forest and a forgotten prince",
        target_difficulty="Detective",
        client=client,
        k=2,
    )
    print(examples)
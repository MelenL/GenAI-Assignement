import os
import logging
import json
import random
import math
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load env variables
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Initialize Client
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
    """
    A retrieval system that uses semantic similarity (embeddings) to find 
    the best matching examples for a given topic.
    Persists embeddings to disk to avoid re-generating them on every restart.
    """
    def __init__(self, data_path=os.path.join(os.path.dirname(__file__), "data\\stories.json"), embeddings_path=os.path.join(os.path.dirname(__file__), "data\\embeddings.json")):
        self.examples = []
        self.embeddings = []  # Cache for example embeddings
        self.data_path = data_path
        self.embeddings_path = embeddings_path
        self.load_data(data_path)

    def load_data(self, path):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.examples = json.load(f)
                logging.info(f"Loaded {len(self.examples)} examples from {path}")
            else:
                logging.warning(f"Data file not found at {path}. RAG will return empty.")
        except Exception as e:
            logging.error(f"Error loading RAG data: {e}")

    def _get_embedding(self, text, client):
        """Generates an embedding vector for a text string using Gemini."""
        try:
            result = client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            # Handle different SDK response structures
            if hasattr(result, 'embeddings'):
                return result.embeddings[0].values
            return []
        except Exception as e:
            logging.warning(f"Embedding failed: {e}")
            return []

    def _cosine_similarity(self, vec1, vec2):
        """Calculates cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _populate_embeddings(self, client):
        """
        Lazy loads embeddings. 
        1. Checks memory. 
        2. Checks disk (embeddings.json). 
        3. Generates via API and saves to disk.
        """
        if self.embeddings:
            return

        # 1. Try Loading from Disk
        if os.path.exists(self.embeddings_path):
            try:
                with open(self.embeddings_path, 'r', encoding='utf-8') as f:
                    loaded_embeddings = json.load(f)
                
                # Basic validation: If example count matches, assume valid. 
                if len(loaded_embeddings) == len(self.examples):
                    self.embeddings = loaded_embeddings
                    logging.info(f"Loaded {len(self.embeddings)} embeddings from disk cache.")
                    return
                else:
                    logging.warning("Cached embeddings count mismatch (data changed?). Regenerating...")
            except Exception as e:
                logging.warning(f"Failed to load embeddings from disk: {e}")

        # 2. Generate via API (if disk load failed or mismatch)
        logging.info("Generating new embeddings via API (one-time setup)...")
        generated_embeddings = []
        for ex in self.examples:
            # Combine topic and short story for a rich semantic representation
            content = f"{ex.get('topic', '')}: {ex.get('short_story', '')}"
            emb = self._get_embedding(content, client)
            generated_embeddings.append(emb)
        
        self.embeddings = generated_embeddings

        # 3. Save to Disk
        try:
            with open(self.embeddings_path, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings, f)
            logging.info(f"Saved embeddings cache to {self.embeddings_path}")
        except Exception as e:
            logging.error(f"Failed to save embeddings cache: {e}")

    def get_examples(self, target_topic, client=None, k=3):
        """
        Retrieves k examples. 
        If client is provided, uses Semantic Search (Embeddings).
        Otherwise, falls back to Keyword Matching.
        """
        if not self.examples:
            return ""

        selected = []

        # --- STRATEGY A: SEMANTIC SEARCH (If Client Available) ---
        if client:
            try:
                # Ensure cache is ready (from disk or API)
                self._populate_embeddings(client)
                
                if self.embeddings and len(self.embeddings) == len(self.examples):
                    # Embed the query
                    query_vec = self._get_embedding(target_topic, client)
                    
                    if query_vec:
                        # Calculate scores
                        scores = []
                        for idx, ex_vec in enumerate(self.embeddings):
                            score = self._cosine_similarity(query_vec, ex_vec)
                            scores.append((score, self.examples[idx]))
                        
                        # Sort by similarity desc
                        scores.sort(key=lambda x: x[0], reverse=True)
                        
                        # Pick top K
                        selected = [item[1] for item in scores[:k]]
                        logging.info(f"RAG: Selected {len(selected)} examples via Semantic Search")
            
            except Exception as e:
                logging.warning(f"Semantic search error: {e}. Falling back to keyword match.")

        # --- STRATEGY B: KEYWORD MATCH (Fallback) ---
        if not selected:
            # Filter by exact string match
            relevant = [ex for ex in self.examples if ex.get('topic', '').lower() == target_topic.lower()]
            others = [ex for ex in self.examples if ex.get('topic', '').lower() != target_topic.lower()]
            random.shuffle(others)

            selected = relevant[:k]
            if len(selected) < k:
                needed = k - len(selected)
                selected.extend(others[:needed])
            logging.info(f"RAG: Selected {len(selected)} examples via Keyword Match")

        # Format output
        formatted_output = ""
        for i, ex in enumerate(selected, 1):
            formatted_output += f"\nExample {i}:\n"
            formatted_output += f"Topic: {ex.get('topic', 'Unknown')}\n"
            formatted_output += f"Difficulty: {ex.get('difficulty', 'Unknown')}\n"
            formatted_output += f"Short Story: {ex.get('short_story')}\n"
            formatted_output += f"Full Story: {ex.get('full_story')}\n"
        
        return formatted_output
    
if __name__ == "__main__":
    RAG_Engine = RAG_Engine()
    if client:
        examples = RAG_Engine.get_examples("Cyberpunk", client=client, k=2)
    else:
        examples = RAG_Engine.get_examples("Cyberpunk", client=None, k=2)
    print(examples)
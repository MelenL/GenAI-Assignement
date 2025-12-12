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
            if hasattr(result, 'embeddings'):
                return result.embeddings[0].values
            return []
        except Exception as e:
            logging.warning(f"Embedding failed: {e}")
            return []

    def _cosine_similarity(self, vec1, vec2):
        if not vec1 or not vec2: return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0 or norm_b == 0: return 0.0
        return dot_product / (norm_a * norm_b)

    def _populate_embeddings(self, client):
        """Lazy loads embeddings. Checks disk cache first, then API."""
        if self.embeddings:
            return

        # 1. Try Loading from Disk
        if os.path.exists(self.embeddings_path):
            try:
                with open(self.embeddings_path, 'r', encoding='utf-8') as f:
                    loaded_embeddings = json.load(f)
                if len(loaded_embeddings) == len(self.examples):
                    self.embeddings = loaded_embeddings
                    logging.info(f"Loaded {len(self.embeddings)} embeddings from disk cache.")
                    return
                else:
                    logging.warning("Cached embeddings count mismatch. Regenerating...")
            except Exception as e:
                logging.warning(f"Failed to load embeddings from disk: {e}")

        # 2. Generate via API
        logging.info("Generating new embeddings via API...")
        generated_embeddings = []
        for ex in self.examples:
            # We embed Topic + Short Story to capture the "Vibe"
            content = f"{ex.get('topic', '')}: {ex.get('short_story', '')}"
            emb = self._get_embedding(content, client)
            generated_embeddings.append(emb)
        
        self.embeddings = generated_embeddings

        # 3. Save to Disk
        try:
            with open(self.embeddings_path, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings, f)
        except Exception as e:
            logging.error(f"Failed to save embeddings cache: {e}")

    def get_examples(self, target_topic, target_difficulty, client=None, k=3):
        """
        Retrieves k examples using Hybrid Filtering:
        1. Filter by Difficulty (Metadata)
        2. Rank by Topic Similarity (Vector)
        """
        if not self.examples:
            return ""

        # --- STEP 1: METADATA FILTERING ---
        # Find indices of examples that match the difficulty
        candidate_indices = [
            i for i, ex in enumerate(self.examples) 
            if ex.get('difficulty', '').lower() == target_difficulty.lower()
        ]

        # Fallback: If not enough exact difficulty matches, use ALL examples
        if len(candidate_indices) < k:
            logging.info(f"Not enough '{target_difficulty}' examples ({len(candidate_indices)}). Searching full database.")
            candidate_indices = range(len(self.examples))
        else:
            logging.info(f"Filtered down to {len(candidate_indices)} '{target_difficulty}' examples.")

        selected_indices = []

        # --- STEP 2: SEMANTIC SEARCH (Vectors) ---
        if client:
            try:
                self._populate_embeddings(client)
                
                if self.embeddings:
                    # Embed the query
                    query_vec = self._get_embedding(target_topic, client)
                    
                    if query_vec:
                        scores = []
                        # Only score the filtered candidates
                        for idx in candidate_indices:
                            score = self._cosine_similarity(query_vec, self.embeddings[idx])
                            scores.append((score, idx))
                        
                        # Sort by similarity
                        scores.sort(key=lambda x: x[0], reverse=True)
                        selected_indices = [item[1] for item in scores[:k]]
            
            except Exception as e:
                logging.warning(f"Semantic search error: {e}")

        # --- STEP 3: FALLBACK (Keyword/Random) ---
        if not selected_indices:
            # If vector search failed, pick random from candidates
            selected_indices = random.sample(candidate_indices, min(k, len(candidate_indices)))

        # Format output
        selected_examples = [self.examples[i] for i in selected_indices]
        
        formatted_output = ""
        for i, ex in enumerate(selected_examples, 1):
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
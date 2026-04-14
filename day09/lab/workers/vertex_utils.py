import os
import vertexai
from vertexai.generative_models import GenerativeModel
from pathlib import Path
from dotenv import load_dotenv

# Load .env once
load_dotenv()

_initialized = False

def init_vertex():
    """
    Initialize Vertex AI using environment variables.
    Ensures initialization happens only once.
    """
    global _initialized
    if _initialized:
        return
    
    # Path to service account JSON
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds:
        creds_path = Path(creds)
        if not creds_path.is_absolute():
            # Resolve relative to lab root (assumed to be one level up from workers/)
            lab_root = Path(__file__).parent.parent
            creds_path = lab_root / creds
        
        if creds_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
    
    # Initialize Vertex AI
    vertexai.init(
        project=os.getenv("VERTEX_PROJECT", "vinai053"),
        location=os.getenv("VERTEX_LOCATION", "us-central1"),
    )
    
    _initialized = True


def call_gemini(user_prompt: str, system_instruction: str = None, temperature: float = 0.0) -> str:
    """
    Standard wrapper to call Gemini model via Vertex AI.
    """
    init_vertex()
    model_id = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")
    
    if system_instruction:
        model = GenerativeModel(
            model_id,
            system_instruction=system_instruction
        )
    else:
        model = GenerativeModel(model_id)
        
    response = model.generate_content(
        user_prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": 800,
        }
    )
    return response.text

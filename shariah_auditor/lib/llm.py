"""
lib/llm.py — Centralised LLM abstraction layer (Gemini)

WHY THIS EXISTS:
Previously each agent imported the Anthropic SDK directly and called
client.messages.create(). Centralising all LLM calls here means:
  - Swapping models = change one file, not four agent files
  - Consistent temperature, token limits, and error handling
  - Easy to add logging, retries, or fallback models later

MIGRATION NOTE:
Switched from Anthropic Claude (claude-sonnet-4-6) to Google Gemini
(gemini-2.0-flash). The system prompt and user message interfaces
are identical — only the underlying SDK call changes.

SETUP:
  Add to .env:  GEMINI_API_KEY=your-key-here
  Get key at:   https://aistudio.google.com/apikey
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure once at module level — reused across all agent calls
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

# Default model — gemini-2.0-flash is fast and capable for JSON tasks
DEFAULT_MODEL = "gemini-2.0-flash"


def chat(
    system:      str,
    user:        str,
    max_tokens:  int   = 3000,
    temperature: float = 0.1,
    model:       str   = DEFAULT_MODEL,
) -> str:
    """
    Makes a single Gemini LLM call and returns the response text.

    Args:
        system:      System prompt — defines the agent's role and output format
        user:        User message — the actual task content (clauses, context, etc.)
        max_tokens:  Maximum output tokens (default 3000 — enough for JSON responses)
        temperature: 0.1 = mostly deterministic (good for structured JSON output)
        model:       Gemini model name — override for specific agents if needed

    Returns:
        Raw response text string (agents call _clean_json() on this if needed)

    Raises:
        google.api_core.exceptions.GoogleAPIError on API failures
    """
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system,
    )

    response = gemini_model.generate_content(
        user,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
    )

    return response.text

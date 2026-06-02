"""
lib/llm.py — Centralised LLM abstraction layer (Groq)

WHY THIS EXISTS:
Previously each agent imported the Anthropic SDK directly and called
client.messages.create(). Centralising all LLM calls here means:
  - Swapping models = change one file, not four agent files
  - Consistent temperature, token limits, and error handling
  - Easy to add logging, retries, or fallback models later

MIGRATION NOTE:
Switched from Google Gemini (gemini-2.0-flash) to Groq
(llama-3.3-70b-versatile). The system prompt and user message
interfaces are identical — only the underlying SDK call changes.
Groq uses the OpenAI-compatible chat completions format.

SETUP:
  Add to .env:  GROQ_API_KEY=your-key-here
  Get key at:   https://console.groq.com/keys
"""

import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Single client instance — reused across all agent calls
_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# llama-3.3-70b-versatile: 128k context, strong instruction following,
# reliable structured JSON output — well suited for compliance auditing
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def chat(
    system:      str,
    user:        str,
    max_tokens:  int   = 3000,
    temperature: float = 0.1,
    model:       str   = DEFAULT_MODEL,
) -> str:
    """
    Makes a single Groq LLM call and returns the response text.

    Args:
        system:      System prompt — defines the agent's role and output format
        user:        User message — the actual task content (clauses, context, etc.)
        max_tokens:  Maximum output tokens (default 3000 — enough for JSON responses)
        temperature: 0.1 = mostly deterministic (good for structured JSON output)
        model:       Groq model name — override for specific agents if needed

    Returns:
        Raw response text string (agents call _clean_json() on this if needed)

    Raises:
        groq.APIError on API failures
    """
    response = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    choice = response.choices[0]
    content = choice.message.content

    # Groq returns None content when finish_reason is "length" (output cut off)
    # or when the request hits a rate limit / content filter
    if not content:
        finish = choice.finish_reason
        raise ValueError(
            f"Groq returned empty response (finish_reason='{finish}'). "
            f"If finish_reason='length', increase max_tokens. "
            f"If None, check your GROQ_API_KEY and rate limits."
        )

    return content


def extract_json(text: str) -> str:
    """
    Robustly extracts a JSON string from an LLM response.

    Handles all the ways llama/Groq can wrap JSON output:
      1. ```json ... ```  or  ``` ... ```  (code block — most common)
      2. Preamble text before the code block ("Here is the JSON:")
      3. Plain JSON with no wrapper (ideal case)

    Returns the innermost JSON string, ready for json.loads().
    Raises ValueError if no JSON structure is found at all.
    """
    text = text.strip()

    # 1. Extract content from a markdown code block (handles preamble before it)
    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_block:
        return code_block.group(1).strip()

    # 2. Find a JSON array anywhere in the text (agents returning lists)
    arr_match = re.search(r'(\[[\s\S]*\])', text)
    if arr_match:
        return arr_match.group(1).strip()

    # 3. Find a JSON object anywhere in the text (simulator returning a dict)
    obj_match = re.search(r'(\{[\s\S]*\})', text)
    if obj_match:
        return obj_match.group(1).strip()

    # 4. Return as-is and let json.loads() produce a clear error
    return text

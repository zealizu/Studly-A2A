import re  # For HTML cleaning (add if missing)
from typing import List, Dict, Any, Optional
from uuid import uuid4  # If needed elsewhere
from models.a2a import A2AMessage, MessagePart

def normalize_telex_message(raw_message: Dict[str, Any]) -> List[A2AMessage]:
    """
    Normalizes Telex's new parts format: parts[0] = query, data = history chunks.
    Returns a clean list of A2AMessage for your agent.
    """
    messages = []
    
    # Debug: Log raw_message structure
    # app.logger.debug(f"Normalizer input: type={type(raw_message)}, has_parts={hasattr(raw_message, 'parts') or 'parts' in raw_message}")
    
    parts = raw_message.get('parts', []) if isinstance(raw_message, dict) else (raw_message.parts if hasattr(raw_message, 'parts') else [])
    if not parts:
        # app.logger.warning("No parts in raw_message - returning empty")
        return messages
    
    # Extract interpreted query (parts[0])
    query_text = ""
    if parts and len(parts) > 0:
        first_part = parts[0]
        kind = first_part.get('kind') if isinstance(first_part, dict) else first_part.kind
        text = first_part.get('text') if isinstance(first_part, dict) else first_part.text
        if kind == 'text' and text:
            query_text = str(text).strip()
    
    # Flatten data part history (last 10 chunks, clean text)
    history_texts = []
    for part in parts:
        # Handle part as dict or model
        is_dict = isinstance(part, dict)
        kind = part.get('kind') if is_dict else part.kind
        if kind == 'data':
            data = part.get('data') if is_dict else part.data
            if isinstance(data, list):
                for sub_item in data[-3:]:  # Last 10 for recency
                    # FIX: Handle sub_item as dict (Telex raw JSON)
                    sub_kind = sub_item.get('kind') if isinstance(sub_item, dict) else getattr(sub_item, 'kind', None)
                    sub_text = sub_item.get('text') if isinstance(sub_item, dict) else getattr(sub_item, 'text', None)
                    if sub_kind == 'text' and sub_text:
                        clean_sub = str(sub_text).strip().replace('<p>', '').replace('</p>', '').replace('<br />', ' ')
                        if clean_sub and clean_sub not in history_texts:
                            history_texts.append(clean_sub)
    
    # Build history messages (alternating roles from history, starting with user)
    full_history = []
    for i, text in enumerate(history_texts):
        role = 'user' if i % 2 == 0 else 'agent'  # Start with user for history
        full_history.append(A2AMessage(role=role, parts=[MessagePart(kind="text", text=text)]))
    
    # Add new query as last user message if present
    if query_text:
        full_history.append(A2AMessage(role="user", parts=[MessagePart(kind="text", text=query_text)]))
    
    messages = full_history
    
    
    return messages
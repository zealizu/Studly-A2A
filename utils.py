import re  # For HTML cleaning (add if missing)
from typing import List, Dict, Any, Optional
from uuid import uuid4  # If needed elsewhere
from models.a2a import A2AMessage, MessagePart
from config import HISTORY_CAP_MESSAGES

def strip_html_and_whitespace(text: str) -> str:
    """
    Aggressively strip HTML tags and normalize whitespace.
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Normalize whitespace (multiple spaces/newlines to single space)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_telex_message(raw_message: Dict[str, Any], history_cap: Optional[int] = None) -> List[A2AMessage]:
    """
    Normalizes Telex's new parts format: parts[0] = query, data = history chunks.
    Returns a clean list of A2AMessage for your agent, capped to recent interactions.
    
    Args:
        raw_message: The raw Telex message with parts
        history_cap: Maximum number of messages to retain (default from config)
    
    Returns:
        List of A2AMessage objects, trimmed to the most recent interactions
    """
    messages = []
    cap = history_cap if history_cap is not None else HISTORY_CAP_MESSAGES
    
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
            query_text = strip_html_and_whitespace(str(text))
    
    # Flatten data part history with aggressive cleaning
    history_texts = []
    for part in parts:
        # Handle part as dict or model
        is_dict = isinstance(part, dict)
        kind = part.get('kind') if is_dict else part.kind
        if kind == 'data':
            data = part.get('data') if is_dict else part.data
            if isinstance(data, list):
                # Apply cap early - only process recent items
                recent_items = data[-(cap * 2):] if len(data) > cap * 2 else data
                for sub_item in recent_items:
                    # FIX: Handle sub_item as dict (Telex raw JSON)
                    sub_kind = sub_item.get('kind') if isinstance(sub_item, dict) else getattr(sub_item, 'kind', None)
                    sub_text = sub_item.get('text') if isinstance(sub_item, dict) else getattr(sub_item, 'text', None)
                    if sub_kind == 'text' and sub_text:
                        clean_sub = strip_html_and_whitespace(str(sub_text))
                        if clean_sub and clean_sub not in history_texts:
                            history_texts.append(clean_sub)
    
    # Build history messages (alternating roles from history, starting with user)
    # Cap to recent history only (exclude the current query for now)
    capped_history_texts = history_texts[-(cap - 1):] if len(history_texts) > (cap - 1) else history_texts
    
    full_history = []
    for i, text in enumerate(capped_history_texts):
        role = 'user' if i % 2 == 0 else 'agent'  # Start with user for history
        full_history.append(A2AMessage(role=role, parts=[MessagePart(kind="text", text=text)]))
    
    # Add new query as last user message if present
    if query_text:
        full_history.append(A2AMessage(role="user", parts=[MessagePart(kind="text", text=query_text)]))
    
    messages = full_history
    # app.logger.info(f"Normalized Telex: Query='{query_text[:50]}...', History chunks={len(history_texts)} -> capped to {len(capped_history_texts)}")
    
    return messages
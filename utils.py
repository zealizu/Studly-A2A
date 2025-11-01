import re  # For HTML cleaning
from typing import List, Dict, Any
from models.a2a import A2AMessage, MessagePart

def normalize_telex_message(raw_message: Dict[str, Any]) -> List[A2AMessage]:
    """
    Normalizes Telex's new parts format: parts[0] = query, data = history chunks.
    Returns a clean list of A2AMessage for your agent.
    """
    messages = []
    if not raw_message or 'parts' not in raw_message:
        return messages
    
    # Extract interpreted query (parts[0])
    query_text = ""
    if raw_message['parts'] and len(raw_message['parts']) > 0 and raw_message['parts'][0].get('kind') == 'text':
        query_text = raw_message['parts'][0]['text'].strip()
    
    # Flatten data part history (last 10 chunks, clean text)
    history_texts = []
    data_part = None
    for part in raw_message['parts']:
        if part.get('kind') == 'data' and isinstance(part.get('data'), list):
            data_part = part
            break
    
    if data_part and data_part['data']:
        for sub_item in data_part['data'][-10:]:  # Last 10 for recency
            if sub_item.get('kind') == 'text' and sub_item.get('text'):
                clean_sub = sub_item['text'].strip().replace('<p>', '').replace('</p>', '').replace('<br />', ' ')
                if clean_sub and clean_sub not in history_texts:
                    history_texts.append(clean_sub)
    
    # Build history messages (alternating roles from history)
    full_history = []
    for i, text in enumerate(history_texts):
        role = 'user' if i % 2 == 0 else 'agent'  # Alternate starting with user
        full_history.append(A2AMessage(role=role, parts=[MessagePart(kind="text", text=text)]))
    
    # Add new query as last user message if present
    if query_text:
        full_history.append(A2AMessage(role="user", parts=[MessagePart(kind="text", text=query_text)]))
    
    messages = full_history
    
    return messages
"""
Benchmark script to measure performance improvements from history trimming.

This script compares:
1. Time to normalize messages (with/without HTML)
2. Time to prepare context (with/without summarization)
3. Memory usage per context
"""

import time
import sys
from typing import List, Dict, Any
from models.a2a import A2AMessage, MessagePart
from utils import normalize_telex_message, strip_html_and_whitespace
from agents.agent import StudlyAgent


def create_large_telex_payload(num_history_items: int = 50, with_html: bool = True) -> Dict[str, Any]:
    """Create a large Telex-style message payload for testing."""
    if with_html:
        history = [
            {'kind': 'text', 'text': f'<p>History message {i} with <b>HTML</b> tags and <br /> formatting</p>'}
            for i in range(num_history_items)
        ]
        query = '<p>Help me create a <b>comprehensive</b> study plan for <i>Python programming</i></p>'
    else:
        history = [
            {'kind': 'text', 'text': f'History message {i}'}
            for i in range(num_history_items)
        ]
        query = 'Help me create a comprehensive study plan for Python programming'
    
    return {
        'parts': [
            {'kind': 'text', 'text': query},
            {'kind': 'data', 'data': history}
        ]
    }


def benchmark_html_stripping():
    """Benchmark HTML stripping performance."""
    print("\n=== HTML Stripping Benchmark ===")
    
    test_cases = [
        "<p>Simple text</p>",
        "<div><p>Nested <b>HTML</b> with <i>multiple</i> tags</p></div>",
        "<p>" + "x" * 1000 + "</p><br /><div>More content</div>",
    ]
    
    for i, text in enumerate(test_cases):
        start = time.perf_counter()
        for _ in range(1000):
            strip_html_and_whitespace(text)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  Test {i+1}: {elapsed:.2f}ms for 1000 calls ({elapsed/1000:.3f}ms per call)")


def benchmark_normalization():
    """Benchmark message normalization with different payload sizes."""
    print("\n=== Message Normalization Benchmark ===")
    
    sizes = [10, 25, 50, 100]
    
    for size in sizes:
        # With HTML
        payload_with_html = create_large_telex_payload(size, with_html=True)
        start = time.perf_counter()
        result_html = normalize_telex_message(payload_with_html)
        time_html = (time.perf_counter() - start) * 1000
        
        # Without HTML (for comparison)
        payload_no_html = create_large_telex_payload(size, with_html=False)
        start = time.perf_counter()
        result_no_html = normalize_telex_message(payload_no_html)
        time_no_html = (time.perf_counter() - start) * 1000
        
        print(f"  {size} history items:")
        print(f"    With HTML:    {time_html:.2f}ms -> {len(result_html)} messages")
        print(f"    Without HTML: {time_no_html:.2f}ms -> {len(result_no_html)} messages")
        print(f"    Overhead:     {time_html - time_no_html:.2f}ms")


def benchmark_context_preparation():
    """Benchmark context preparation with different history sizes."""
    print("\n=== Context Preparation Benchmark ===")
    
    agent = StudlyAgent()
    
    sizes = [2, 4, 8, 12, 16]
    
    for size in sizes:
        # Create messages
        messages = [
            A2AMessage(role="user" if i % 2 == 0 else "agent",
                      parts=[MessagePart(kind="text", text=f"Message {i} with some content")])
            for i in range(size)
        ]
        # Add current query
        messages.append(A2AMessage(role="user", parts=[MessagePart(kind="text", text="Current query")]))
        
        # Measure first call (may generate summary)
        start = time.perf_counter()
        context1 = agent._prepare_context(messages, f"context-{size}")
        time1 = (time.perf_counter() - start) * 1000
        
        # Measure second call (should use cache if applicable)
        start = time.perf_counter()
        context2 = agent._prepare_context(messages, f"context-{size}")
        time2 = (time.perf_counter() - start) * 1000
        
        print(f"  {size} messages:")
        print(f"    First call:  {time1:.2f}ms")
        print(f"    Second call: {time2:.2f}ms (cache hit)")
        print(f"    Speedup:     {time1/time2:.1f}x")


def estimate_token_savings():
    """Estimate token savings from history trimming."""
    print("\n=== Estimated Token Savings ===")
    
    # Rough estimate: ~4 chars per token on average
    def estimate_tokens(messages: List[A2AMessage]) -> int:
        total_chars = sum(
            len(msg.parts[0].text)
            for msg in messages
            if msg.parts and msg.parts[0].kind == "text"
        )
        return total_chars // 4
    
    sizes = [20, 50, 100]
    
    for size in sizes:
        # Create large payload
        payload = create_large_telex_payload(size, with_html=True)
        
        # Normalize (with trimming)
        normalized = normalize_telex_message(payload)
        
        # Estimate tokens
        tokens_with_trimming = estimate_tokens(normalized)
        
        # Estimate what it would be without trimming (approximate)
        # Assume all history would be kept
        approx_chars_without_trimming = size * 100  # Rough estimate
        tokens_without_trimming = approx_chars_without_trimming // 4
        
        savings = tokens_without_trimming - tokens_with_trimming
        savings_pct = (savings / tokens_without_trimming * 100) if tokens_without_trimming > 0 else 0
        
        print(f"  {size} history items:")
        print(f"    Without trimming: ~{tokens_without_trimming} tokens")
        print(f"    With trimming:    ~{tokens_with_trimming} tokens")
        print(f"    Savings:          ~{savings} tokens ({savings_pct:.1f}%)")


def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("History Trimming Performance Benchmark")
    print("=" * 60)
    
    try:
        benchmark_html_stripping()
        benchmark_normalization()
        benchmark_context_preparation()
        estimate_token_savings()
        
        print("\n" + "=" * 60)
        print("Benchmark complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during benchmark: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

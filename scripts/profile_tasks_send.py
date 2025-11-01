#!/usr/bin/env python3
"""
Performance profiling script for /tasks/send endpoint.

Usage:
    python scripts/profile_tasks_send.py [--url URL] [--requests N] [--output FILE]

Example:
    python scripts/profile_tasks_send.py --url http://localhost:5000 --requests 10
"""

import requests
import time
import json
import statistics
import argparse
from typing import List, Dict, Any


def create_sample_payloads() -> List[Dict[str, Any]]:
    """Create representative test payloads for the /tasks/send endpoint."""
    return [
        {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "messageId": "msg-1",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Create a study plan for learning Python in 30 days"
                        }
                    ]
                },
                "configuration": {
                    "blocking": True,
                    "acceptedOutputModes": ["text/plain"]
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "test-2",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "messageId": "msg-2",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Help me prepare for a machine learning interview"
                        }
                    ]
                },
                "configuration": {
                    "blocking": True,
                    "acceptedOutputModes": ["text/plain"]
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "test-3",
            "method": "execute",
            "params": {
                "contextId": "context-123",
                "taskId": "task-456",
                "messages": [
                    {
                        "kind": "message",
                        "role": "user",
                        "parts": [
                            {
                                "kind": "text",
                                "text": "I want to learn data structures and algorithms"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "test-4",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "messageId": "msg-4",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Quick study plan for AWS certification"
                        }
                    ]
                },
                "configuration": {
                    "blocking": True,
                    "acceptedOutputModes": ["text/plain"]
                }
            }
        }
    ]


def profile_request(url: str, payload: Dict[str, Any]) -> Dict[str, float]:
    """Send a single request and measure latency."""
    start_time = time.perf_counter()
    
    try:
        response = requests.post(
            f"{url}/tasks/send",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        end_time = time.perf_counter()
        latency = end_time - start_time
        
        return {
            "latency": latency,
            "status_code": response.status_code,
            "success": response.status_code == 200
        }
    except requests.exceptions.RequestException as e:
        end_time = time.perf_counter()
        return {
            "latency": end_time - start_time,
            "status_code": 0,
            "success": False,
            "error": str(e)
        }


def run_profiling(url: str, num_requests: int, output_file: str = None) -> None:
    """Run profiling tests and report statistics."""
    print(f"🚀 Starting profiling against {url}")
    print(f"📊 Running {num_requests} requests...\n")
    
    payloads = create_sample_payloads()
    results = []
    
    for i in range(num_requests):
        payload = payloads[i % len(payloads)]
        print(f"Request {i+1}/{num_requests}... ", end="", flush=True)
        
        result = profile_request(url, payload)
        results.append(result)
        
        if result["success"]:
            print(f"✓ {result['latency']*1000:.2f}ms")
        else:
            print(f"✗ Failed (status: {result['status_code']})")
    
    # Calculate statistics
    successful_results = [r for r in results if r["success"]]
    latencies = [r["latency"] for r in successful_results]
    
    if not latencies:
        print("\n❌ No successful requests to analyze")
        return
    
    # Sort for percentile calculations
    latencies.sort()
    
    stats = {
        "total_requests": num_requests,
        "successful_requests": len(successful_results),
        "failed_requests": num_requests - len(successful_results),
        "mean_latency_ms": statistics.mean(latencies) * 1000,
        "median_latency_ms": statistics.median(latencies) * 1000,
        "min_latency_ms": min(latencies) * 1000,
        "max_latency_ms": max(latencies) * 1000,
        "p95_latency_ms": latencies[int(len(latencies) * 0.95)] * 1000 if len(latencies) > 1 else latencies[0] * 1000,
        "p99_latency_ms": latencies[int(len(latencies) * 0.99)] * 1000 if len(latencies) > 1 else latencies[0] * 1000,
    }
    
    if len(latencies) > 1:
        stats["stddev_latency_ms"] = statistics.stdev(latencies) * 1000
    else:
        stats["stddev_latency_ms"] = 0
    
    # Print results
    print("\n" + "="*60)
    print("📈 PROFILING RESULTS")
    print("="*60)
    print(f"Total Requests:       {stats['total_requests']}")
    print(f"Successful:           {stats['successful_requests']}")
    print(f"Failed:               {stats['failed_requests']}")
    print(f"\nLatency Statistics (ms):")
    print(f"  Mean:               {stats['mean_latency_ms']:.2f}")
    print(f"  Median:             {stats['median_latency_ms']:.2f}")
    print(f"  Min:                {stats['min_latency_ms']:.2f}")
    print(f"  Max:                {stats['max_latency_ms']:.2f}")
    print(f"  Std Dev:            {stats['stddev_latency_ms']:.2f}")
    print(f"  P95:                {stats['p95_latency_ms']:.2f}")
    print(f"  P99:                {stats['p99_latency_ms']:.2f}")
    print("="*60)
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"\n💾 Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Profile /tasks/send endpoint latency"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="Base URL of the server (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=10,
        help="Number of requests to send (default: 10)"
    )
    parser.add_argument(
        "--output",
        help="Output file to save results (JSON format)"
    )
    
    args = parser.parse_args()
    
    # Verify server is reachable
    try:
        response = requests.get(args.url, timeout=5)
        print(f"✓ Server is reachable at {args.url}\n")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach server at {args.url}")
        print(f"Error: {e}")
        print("\nMake sure the server is running with:")
        print("  python app.py")
        print("or:")
        print("  gunicorn app:app")
        return
    
    run_profiling(args.url, args.requests, args.output)


if __name__ == "__main__":
    main()

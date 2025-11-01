#!/usr/bin/env python3
"""
Simple load testing script for the async Gemini pipeline.
Tests /tasks/send endpoint with concurrent requests.
"""
import asyncio
import aiohttp
import time
import json
import statistics
from typing import List, Dict
import sys


async def send_request(session: aiohttp.ClientSession, url: str, request_id: str) -> Dict:
    """Send a single request and measure response time"""
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "execute",
        "params": {
            "messages": [
                {
                    "kind": "message",
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Help me learn Python basics in 1 week"
                        }
                    ]
                }
            ]
        }
    }
    
    start_time = time.time()
    try:
        async with session.post(url, json=payload) as response:
            response_data = await response.json()
            elapsed = time.time() - start_time
            
            return {
                "request_id": request_id,
                "status_code": response.status,
                "elapsed": elapsed,
                "success": response.status == 200,
                "error": response_data.get("error") if response.status != 200 else None
            }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "request_id": request_id,
            "status_code": 0,
            "elapsed": elapsed,
            "success": False,
            "error": str(e)
        }


async def run_load_test(url: str, num_requests: int = 20, concurrency: int = 5):
    """Run concurrent load test"""
    print(f"\n{'='*60}")
    print(f"Load Testing: {url}")
    print(f"Total Requests: {num_requests}")
    print(f"Concurrency: {concurrency}")
    print(f"{'='*60}\n")
    
    async with aiohttp.ClientSession() as session:
        # Create all tasks
        tasks = []
        for i in range(num_requests):
            task = send_request(session, url, f"req-{i}")
            tasks.append(task)
        
        # Run with limited concurrency
        results = []
        for i in range(0, len(tasks), concurrency):
            batch = tasks[i:i+concurrency]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
            
            # Progress indicator
            completed = min(i + concurrency, num_requests)
            print(f"Progress: {completed}/{num_requests} requests completed")
    
    # Calculate statistics
    elapsed_times = [r["elapsed"] for r in results]
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    timeouts = [r for r in failed if r["status_code"] == 408]
    
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Total Requests: {len(results)}")
    print(f"Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
    print(f"Timeouts: {len(timeouts)}")
    print(f"\nLatency Statistics:")
    print(f"  Min: {min(elapsed_times):.2f}s")
    print(f"  Max: {max(elapsed_times):.2f}s")
    print(f"  Mean: {statistics.mean(elapsed_times):.2f}s")
    print(f"  Median: {statistics.median(elapsed_times):.2f}s")
    if len(elapsed_times) > 1:
        print(f"  StdDev: {statistics.stdev(elapsed_times):.2f}s")
    
    # Check if target metrics are met
    avg_latency = statistics.mean(elapsed_times)
    print(f"\n{'='*60}")
    print("TARGET METRICS")
    print(f"{'='*60}")
    print(f"Average Latency: {avg_latency:.2f}s (Target: <5s)")
    print(f"Status: {'✓ PASS' if avg_latency < 5.0 else '✗ FAIL'}")
    
    # Show some failed requests details if any
    if failed:
        print(f"\n{'='*60}")
        print("FAILED REQUESTS (first 5)")
        print(f"{'='*60}")
        for r in failed[:5]:
            print(f"  {r['request_id']}: {r['error']}")
    
    print(f"\n{'='*60}\n")
    
    return {
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "avg_latency": avg_latency,
        "meets_target": avg_latency < 5.0
    }


async def main():
    """Main entry point"""
    # Default configuration
    url = "http://localhost:5000/tasks/send"
    num_requests = 20
    concurrency = 5
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        url = sys.argv[1]
    if len(sys.argv) > 2:
        num_requests = int(sys.argv[2])
    if len(sys.argv) > 3:
        concurrency = int(sys.argv[3])
    
    results = await run_load_test(url, num_requests, concurrency)
    
    # Exit with error code if targets not met
    sys.exit(0 if results["meets_target"] else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nLoad test interrupted by user")
        sys.exit(1)

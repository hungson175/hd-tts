#!/usr/bin/env python3
"""
Measure FRONTEND API call time (includes base64 overhead).
"""

import time
import requests

FRONTEND_API = "http://localhost:3341/api/generate-speech"
BOSS_TEXT = "Tiếp theo, bạn sẽ được làm quen với Facebook Ads Manager, để hiểu rõ cấu trúc và cách thiết lập campaign, ad set và ad. Sau đó, chúng ta sẽ phân tích các định dạng quảng cáo khác nhau và những best practices khi chạy ads cho nghệ sĩ."

print("Testing FRONTEND API (matches UI experience)...\n")

times = []
for i in range(1, 4):
    payload = {
        "text": BOSS_TEXT,
        "gender": "female",
        "accent": "northern",
        "emotion": "neutral",
        "quality": "high",
        "speed": 1.0
    }

    print(f"Test {i}...", end=" ", flush=True)
    start = time.time()
    response = requests.post(FRONTEND_API, json=payload)
    end = time.time()

    duration = end - start
    times.append(duration)

    if response.status_code == 200:
        data = response.json()
        gen_time = data.get("metadata", {}).get("generationTime")
        print(f"✓ TOTAL: {duration:.2f}s (backend reported: {gen_time}s)")
    else:
        print(f"✗ FAILED")

if times:
    avg = sum(times) / len(times)
    print(f"\n{'='*60}")
    print("FRONTEND API TIMING (matches UI)")
    print(f"{'='*60}")
    print(f"Test 1: {times[0]:.2f}s")
    print(f"Test 2: {times[1]:.2f}s")
    print(f"Test 3: {times[2]:.2f}s")
    print(f"Average TOTAL: {avg:.2f}s")
    print(f"\nBoss reported: ~13s")
    print(f"Match: {'YES ✓' if abs(avg - 13) < 2 else 'NO - investigating'}")
    print(f"{'='*60}")

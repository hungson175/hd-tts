#!/usr/bin/env python3
"""
VERIFY CALIBRATION - Run Boss's exact text and prove the results.
"""

import time
import requests
import json

API_URL = "http://localhost:17603/synthesize"

# Boss's EXACT text
BOSS_TEXT = "Tiếp theo, bạn sẽ được làm quen với Facebook Ads Manager, để hiểu rõ cấu trúc và cách thiết lập campaign, ad set và ad. Sau đó, chúng ta sẽ phân tích các định dạng quảng cáo khác nhau và những best practices khi chạy ads cho nghệ sĩ."

def count_words(text):
    return len(text.split())

word_count = count_words(BOSS_TEXT)
print(f"Boss's text: {word_count} words")
print(f"Text: {BOSS_TEXT}\n")

print("Running 3 tests with HIGH quality (NFE=32)...\n")

times = []
for i in range(1, 4):
    payload = {
        "text": BOSS_TEXT,
        "gender": "female",
        "area": "northern",
        "emotion": "neutral",
        "quality": "high",  # NFE=32
        "speed": 1.0
    }

    print(f"Test {i}...", end=" ", flush=True)
    start = time.time()
    response = requests.post(API_URL, json=payload)
    end = time.time()

    duration = end - start
    times.append(duration)

    if response.status_code == 200:
        print(f"✓ {duration:.2f}s ({duration/word_count:.4f}s/word)")
    else:
        print(f"✗ FAILED (status {response.status_code})")

if times:
    avg_time = sum(times) / len(times)
    avg_per_word = avg_time / word_count

    print(f"\n{'='*60}")
    print("PROOF OF CALIBRATION")
    print(f"{'='*60}")
    print(f"Word count: {word_count}")
    print(f"Test 1: {times[0]:.2f}s")
    if len(times) > 1:
        print(f"Test 2: {times[1]:.2f}s")
    if len(times) > 2:
        print(f"Test 3: {times[2]:.2f}s")
    print(f"\nAverage: {avg_time:.2f}s")
    print(f"Time per word: {avg_per_word:.4f}s")
    print(f"{'='*60}")

    # What would estimate be?
    estimate = word_count * avg_per_word
    print(f"\nEstimate for future {word_count}-word text: {estimate:.2f}s")
    print(f"Boss reported: ~13s")
    print(f"Discrepancy: {13 - avg_time:.2f}s")

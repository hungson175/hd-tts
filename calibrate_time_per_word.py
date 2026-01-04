#!/usr/bin/env python3
"""
Calibrate time-per-word for TTS generation.
Runs actual generation tests and measures real performance.
"""

import time
import requests
import json

# Backend API endpoint
API_URL = "http://localhost:17603/synthesize"

# 3 test samples (30-50 words each)
SAMPLES = [
    # Sample 1: 35 words
    "Chào mừng bạn đến với hệ thống chuyển đổi văn bản thành giọng nói. Công nghệ AI hiện đại cho phép tạo ra giọng đọc tự nhiên và sống động. Chúng tôi cung cấp nhiều giọng đọc khác nhau để bạn lựa chọn.",

    # Sample 2: 42 words
    "Tiếp theo, bạn sẽ được làm quen với Facebook Ads Manager, để hiểu rõ cấu trúc và cách thiết lập campaign, ad set và ad. Sau đó, chúng ta sẽ phân tích các định dạng quảng cáo khác nhau và những best practices khi chạy ads cho nghệ sĩ.",

    # Sample 3: 38 words
    "Trong thời đại công nghệ số, việc ứng dụng trí tuệ nhân tạo vào cuộc sống ngày càng phổ biến. Từ các trợ lý ảo cho đến xe tự lái, AI đang thay đổi cách chúng ta làm việc và sinh hoạt hàng ngày."
]

def count_words(text):
    """Count Vietnamese words in text."""
    return len(text.split())

def generate_speech(text, quality="high"):
    """Call TTS API and measure generation time."""
    payload = {
        "text": text,
        "gender": "female",
        "area": "northern",
        "emotion": "neutral",
        "quality": quality,
        "speed": 1.0
    }

    start_time = time.time()
    response = requests.post(API_URL, json=payload)
    end_time = time.time()

    if response.status_code == 200:
        duration = end_time - start_time
        return duration, True
    else:
        return 0, False

def main():
    print("=== TTS Time-Per-Word Calibration ===\n")

    total_time = 0
    total_words = 0
    all_results = []

    for i, sample in enumerate(SAMPLES, 1):
        word_count = count_words(sample)
        print(f"\nSample {i}: {word_count} words")
        print(f"Text: {sample[:60]}...")

        # Run 2 generations per sample
        for run in range(1, 3):
            print(f"  Run {run}...", end=" ", flush=True)
            duration, success = generate_speech(sample, quality="high")

            if success:
                print(f"✓ {duration:.2f}s")
                total_time += duration
                total_words += word_count
                all_results.append({
                    "sample": i,
                    "run": run,
                    "words": word_count,
                    "time": duration,
                    "time_per_word": duration / word_count
                })
            else:
                print("✗ FAILED")

    # Calculate overall average
    if total_words > 0:
        avg_time_per_word = total_time / total_words

        print("\n" + "="*50)
        print("CALIBRATION RESULTS")
        print("="*50)
        print(f"Total generations: {len(all_results)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Total words: {total_words}")
        print(f"\n>>> AVERAGE TIME PER WORD: {avg_time_per_word:.4f}s <<<")
        print("="*50)

        print("\nDetailed results:")
        for r in all_results:
            print(f"  Sample {r['sample']}, Run {r['run']}: {r['words']} words, {r['time']:.2f}s, {r['time_per_word']:.4f}s/word")

        print(f"\nUpdate TIME_PER_WORD constant to: {avg_time_per_word:.4f}")
    else:
        print("\n✗ No successful generations. Check if backend is running.")

if __name__ == "__main__":
    main()

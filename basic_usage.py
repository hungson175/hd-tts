#!/usr/bin/env python3
"""
Basic usage example for VietVoice TTS
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
import vietvoicetts
from vietvoicetts import ModelConfig, TTSApi

def basic_example():
    """Basic TTS synthesis example"""
    print("=== Basic TTS Example ===")
    
    text = "Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt."
    output_path = "basic_output.wav"
    
    try:
        # Simple synthesis using convenience function
        generation_time = vietvoicetts.synthesize(
            text=text,
            output_path=output_path,
            gender="female",
            # group="story",
            # area="northern",
            emotion="surprised"
        )
        
        print(f"✅ Synthesis completed in {generation_time:.2f} seconds")
        print(f"📁 Audio saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def basic_example_with_reference():
    """Basic TTS synthesis example with reference audio"""
    print("=== Basic TTS Example with Reference ===")
    
    text = "Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt."
    output_path = "basic_output_with_reference.wav"
    
    # Check if reference file exists
    reference_audio_path = './examples/sample.m4a'
    if not Path(reference_audio_path).exists():
        print(f"⚠️  Reference audio file not found: {reference_audio_path}")
        print("Using built-in voice samples instead...")
        
        try:
            # Use built-in samples instead
            generation_time = vietvoicetts.synthesize(
                text=text,
                output_path=output_path,
                gender="female",
                emotion="happy"
            )
            
            print(f"✅ Synthesis completed in {generation_time:.2f} seconds")
            print(f"📁 Audio saved to: {output_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    else:
        try:
            # Use reference audio if available
            generation_time = vietvoicetts.synthesize(
                text=text,
                output_path=output_path,
                reference_audio=reference_audio_path,
                reference_text='Xin chào các anh chị và các bạn. Chào mừng các anh chị đến với podcast Hiếu TV. Trước khi bắt đầu, dành cho anh chị nào mới lần đầu đến podcast này.'
            )
            
            print(f"✅ Synthesis completed in {generation_time:.2f} seconds")
            print(f"📁 Audio saved to: {output_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    return True


def custom_config_example():
    """Example with custom configuration"""
    print("\n=== Custom Configuration Example ===")
    
    # Create custom configuration using ModelConfig
    config = ModelConfig(
        speed=1.2,                    # Speak 20% faster
        random_seed=9999
    )
    
    text = "Đây là ví dụ với cấu hình tùy chỉnh. Tốc độ nói sẽ nhanh hơn 20% so với bình thường."
    output_path = "custom_config_output.wav"
    
    try:
        with TTSApi(config) as tts:
            # Validate configuration first
            if not tts.validate_configuration():
                print("❌ Configuration validation failed")
                return False
            
            # Synthesize with custom config - returns (audio_data, generation_time)
            audio_data, generation_time = tts.synthesize(
                text=text,
                output_path=output_path,
                # reference_audio='./examples/sample.m4a',
                # reference_text='Xin chào các anh chị và các bạn. Chào mừng các anh chị đến với podcast Hiếu TV. Trước khi bắt đầu, dành cho anh chị nào mới lần đầu đến podcast này.'
            )
            
            print(f"✅ Synthesis completed in {generation_time:.2f} seconds")
            print(f"📁 Audio saved to: {output_path}")
            print(f"🎵 Audio array shape: {audio_data.shape}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


def long_text_example():
    """Example with long text that will be chunked"""
    print("\n=== Long Text Example ===")
    
    long_text = """    
    Việt Nam có nền văn hóa phong phú với lịch sử hàng ngàn năm. 
    Đất nước này nổi tiếng với các món ăn đặc sắc như phở, bánh mì, bún chả và nhiều món ngon khác.
   
    Kinh tế Việt Nam đang phát triển mạnh mẽ với các ngành công nghiệp chế xuất, nông nghiệp và du lịch.
    Việt Nam cũng là thành viên của nhiều tổ chức quốc tế quan trọng như ASEAN, WTO và UN.
    """
    
    output_path = "long_text_output.wav"
    
    config = ModelConfig(
        max_chunk_duration=20.0,
        cross_fade_duration=0.15
    )
    
    try:
        with TTSApi(config) as tts:
            # Use synthesize_to_file for just getting the generation time
            generation_time = tts.synthesize_to_file(
                text=long_text.strip(),
                output_path=output_path,
                gender="female",
            )
            
            print(f"✅ Long text synthesis completed in {generation_time:.2f} seconds")
            print(f"📁 Audio saved to: {output_path}")
            print("🔧 Text was automatically chunked and cross-faded")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


def bytes_output_example():
    """Example returning audio as bytes instead of file"""
    print("\n=== Bytes Output Example ===")
    
    text = "Ví dụ này trả về dữ liệu âm thanh dưới dạng bytes thay vì lưu file."
    
    # Check if reference file exists
    reference_audio_path = './examples/sample.m4a'
    if not Path(reference_audio_path).exists():
        print(f"⚠️  Reference audio file not found: {reference_audio_path}")
        print("Using built-in voice samples instead...")
        
        try:
            # Use built-in samples instead
            audio_bytes, generation_time = vietvoicetts.synthesize_to_bytes(
                text=text,
                gender="male",
                emotion="neutral"
            )
            
            print(f"✅ Synthesis completed in {generation_time:.2f} seconds")
            print(f"📊 Audio bytes length: {len(audio_bytes)} bytes")
            print(f"💾 Can be used for streaming or in-memory processing")
            
            # Save bytes to file
            bytes_output_path = "bytes_output.wav"
            with open(bytes_output_path, 'wb') as f:
                f.write(audio_bytes)
            print(f"📁 Bytes also saved to: {bytes_output_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    else:
        try:
            # Use reference audio if available
            audio_bytes, generation_time = vietvoicetts.synthesize_to_bytes(
                text=text,
                reference_audio=reference_audio_path,
                reference_text='Xin chào các anh chị và các bạn. Chào mừng các anh chị đến với podcast Hiếu TV. Trước khi bắt đầu, dành cho anh chị nào mới lần đầu đến podcast này.'
            )
            
            print(f"✅ Synthesis completed in {generation_time:.2f} seconds")
            print(f"📊 Audio bytes length: {len(audio_bytes)} bytes")
            print(f"💾 Can be used for streaming or in-memory processing")
            
            # Save bytes to file
            bytes_output_path = "bytes_output.wav"
            with open(bytes_output_path, 'wb') as f:
                f.write(audio_bytes)
            print(f"📁 Bytes also saved to: {bytes_output_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    return True


def main():
    """Run all examples"""
    print("🎙️  VietVoice TTS Examples")
    print("=" * 50)
        
    examples = [
        ("Basic Usage", basic_example),
        ("Basic Usage with Reference", basic_example_with_reference),
        ("Custom Configuration", custom_config_example),
        ("Long Text Processing", long_text_example),
        ("Bytes Output", bytes_output_example)
    ]
    
    results = []
    for name, example_func in examples:
        try:
            success = example_func()
            results.append((name, success))
        except KeyboardInterrupt:
            print("\n⏹️  Examples interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Summary:")
    for name, success in results:
        status = "✅ Success" if success else "❌ Failed"
        print(f"   {name}: {status}")
    
    successful_count = sum(1 for _, success in results if success)
    print(f"\n🎯 {successful_count}/{len(results)} examples completed successfully")
    
    return successful_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
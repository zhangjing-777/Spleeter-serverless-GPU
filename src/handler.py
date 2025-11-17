import runpod
import base64
import tempfile
import os
import zipfile
import shutil
from pydub import AudioSegment
from predict import separate_audio

def compress_audio(input_path, output_path, target_bitrate="192k"):
    """
    压缩音频为 MP3
    使用 192k 保证钢琴音质
    """
    try:
        print(f"Compressing {os.path.basename(input_path)} to MP3 at {target_bitrate}...")
        audio = AudioSegment.from_wav(input_path)
        audio.export(output_path, format="mp3", bitrate=target_bitrate)
        
        original_size = os.path.getsize(input_path)
        compressed_size = os.path.getsize(output_path)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        print(f"  Original: {original_size / 1024:.2f} KB")
        print(f"  Compressed: {compressed_size / 1024:.2f} KB")
        print(f"  Saved: {compression_ratio:.1f}%")
        
        return True
    except Exception as e:
        print(f"Error compressing {input_path}: {e}")
        return False

def handler(event):
    """
    RunPod Serverless Entry
    Expected input:
    {
        "input": {
            "audio_base64": "<base64 audio>",
            "stems": 5,  // 2, 4, or 5
            "format": "mp3",  // "mp3" or "wav"
            "bitrate": "192k"  // "128k", "192k", "256k", or "320k"
        }
    }
    """
    try:
        print("=" * 60)
        print("Received separation request")
        
        # Parse input
        audio_b64 = event["input"]["audio_base64"]
        stems = event["input"].get("stems", 5)  # 默认 5 stems（包含钢琴）
        output_format = event["input"].get("format", "mp3")
        bitrate = event["input"].get("bitrate", "192k")  # 高质量默认值
        
        audio_bytes = base64.b64decode(audio_b64)
        audio_size_mb = len(audio_bytes) / 1024 / 1024
        
        print(f"Audio size: {audio_size_mb:.2f} MB")
        print(f"Stems: {stems}")
        print(f"Output format: {output_format}")
        print(f"Bitrate: {bitrate}")
        print("=" * 60)

        # Save uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            audio_path = f.name
        
        print(f"Saved audio to {audio_path}")

        # Separate audio
        output_dir = separate_audio(audio_path, stems)
        print(f"Separation complete")
        
        # Collect all output files
        output_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.wav'):
                    output_files.append(os.path.join(root, file))
        
        print(f"Found {len(output_files)} output files")
        
        # Create ZIP with compressed or original audio
        zip_path = tempfile.mktemp(suffix=".zip")
        file_list = []
        
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for wav_path in output_files:
                file_name = os.path.basename(wav_path)
                
                if output_format == "mp3":
                    # Convert to MP3
                    mp3_name = file_name.replace('.wav', '.mp3')
                    mp3_path = os.path.join(os.path.dirname(wav_path), mp3_name)
                    
                    if compress_audio(wav_path, mp3_path, target_bitrate=bitrate):
                        mp3_size = os.path.getsize(mp3_path)
                        zipf.write(mp3_path, mp3_name)
                        file_list.append({
                            "name": mp3_name,
                            "size_kb": round(mp3_size / 1024, 2)
                        })
                        os.unlink(mp3_path)
                    else:
                        # Fallback to WAV if compression fails
                        print(f"  Compression failed, using WAV")
                        wav_size = os.path.getsize(wav_path)
                        zipf.write(wav_path, file_name)
                        file_list.append({
                            "name": file_name,
                            "size_kb": round(wav_size / 1024, 2)
                        })
                else:
                    # Keep as WAV
                    wav_size = os.path.getsize(wav_path)
                    zipf.write(wav_path, file_name)
                    file_list.append({
                        "name": file_name,
                        "size_kb": round(wav_size / 1024, 2)
                    })
        
        # Check ZIP size
        zip_size = os.path.getsize(zip_path)
        zip_size_mb = zip_size / 1024 / 1024
        print(f"\nZIP file created: {zip_size_mb:.2f} MB")
        
        # Check if within API limit (10MB)
        if zip_size > 10 * 1024 * 1024:
            os.unlink(audio_path)
            os.unlink(zip_path)
            shutil.rmtree(output_dir)
            
            return {
                "error": f"Output files too large ({zip_size_mb:.2f} MB exceeds 10MB limit)",
                "size_mb": round(zip_size_mb, 2),
                "files": file_list,
                "suggestions": [
                    "Try shorter audio clips (< 2 minutes)",
                    "Use lower bitrate: 128k or 160k",
                    "Use fewer stems (2 or 4 instead of 5)"
                ]
            }
        
        # Convert ZIP to base64
        print("Encoding to base64...")
        with open(zip_path, "rb") as f:
            zip_b64 = base64.b64encode(f.read()).decode()
        
        base64_size_mb = len(zip_b64) / 1024 / 1024
        print(f"Base64 size: {base64_size_mb:.2f} MB")
        
        # Cleanup
        try:
            os.unlink(audio_path)
            os.unlink(zip_path)
            shutil.rmtree(output_dir)
            print("Cleanup completed")
        except Exception as e:
            print(f"Cleanup warning: {e}")
        
        print("=" * 60)
        print("Request completed successfully!")
        print("=" * 60)
        
        return {
            "zip_base64": zip_b64,
            "format": output_format,
            "bitrate": bitrate if output_format == "mp3" else "N/A",
            "stems": stems,
            "size_mb": round(zip_size_mb, 2),
            "files": file_list
        }
    
    except Exception as e:
        print("=" * 60)
        print(f"ERROR: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    print("Starting RunPod Spleeter serverless handler...")
    print("Supported stems: 2, 4, 5")
    print("Default: 5 stems (includes piano separation)")
    runpod.serverless.start({"handler": handler})

import runpod
import base64
import tempfile
import os
import zipfile
import shutil
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from pydub import AudioSegment
from predict import separate_audio

def compress_audio(input_path, output_path, target_bitrate="192k"):
    """压缩音频为 MP3"""
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

def upload_to_s3(file_path, bucket_name, object_key, expire_seconds=3600):
    """
    上传文件到 S3 并返回预签名 URL
    
    Args:
        file_path: 本地文件路径
        bucket_name: S3 bucket 名称
        object_key: S3 对象键（路径）
        expire_seconds: 预签名 URL 过期时间（秒）
    
    Returns:
        dict: {"url": "预签名URL", "key": "S3对象键", "expires_at": "过期时间ISO格式"}
    """
    try:
        # 从环境变量获取 AWS 凭证
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        
        if not aws_access_key or not aws_secret_key:
            raise ValueError("AWS credentials not found in environment variables")
        
        # 创建 S3 客户端
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        # 上传文件
        print(f"Uploading to S3: s3://{bucket_name}/{object_key}")
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size / 1024 / 1024:.2f} MB")
        
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            object_key,
            ExtraArgs={'ContentType': 'application/zip'}
        )
        
        print("Upload successful!")
        
        # 生成预签名 URL
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expire_seconds
        )
        
        expires_at = (datetime.utcnow() + timedelta(seconds=expire_seconds)).isoformat() + "Z"
        
        print(f"Generated presigned URL (expires in {expire_seconds}s)")
        
        return {
            "url": download_url,
            "key": object_key,
            "bucket": bucket_name,
            "expires_at": expires_at,
            "size_mb": round(file_size / 1024 / 1024, 2)
        }
        
    except ClientError as e:
        print(f"S3 upload error: {e}")
        raise Exception(f"Failed to upload to S3: {str(e)}")
    except Exception as e:
        print(f"Error: {e}")
        raise

def handler(event):
    """
    RunPod Serverless Entry
    
    Expected input:
    {
        "input": {
            "audio_base64": "<base64 audio>",
            "stems": 5,  // 2, 4, or 5
            "format": "mp3",  // "mp3" or "wav"
            "bitrate": "192k",  // "128k", "160k", "192k", "256k", "320k"
            "expire_hours": 1  // S3 URL 过期时间（小时）
        }
    }
    
    Required Environment Variables:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_REGION (optional, default: us-east-1)
    - S3_BUCKET_NAME
    """
    try:
        print("=" * 60)
        print("Received separation request")
        
        # Parse input
        audio_b64 = event["input"]["audio_base64"]
        stems = event["input"].get("stems", 5)
        output_format = event["input"].get("format", "mp3")
        bitrate = event["input"].get("bitrate", "192k")
        expire_hours = event["input"].get("expire_hours", 1)
        
        audio_bytes = base64.b64decode(audio_b64)
        audio_size_mb = len(audio_bytes) / 1024 / 1024
        
        print(f"Audio size: {audio_size_mb:.2f} MB")
        print(f"Stems: {stems}")
        print(f"Output format: {output_format}")
        print(f"Bitrate: {bitrate}")
        print(f"URL expiration: {expire_hours} hour(s)")
        print("=" * 60)

        # Get S3 bucket from environment
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable not set")

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
        
        # Create ZIP with compressed audio
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
                        # Fallback to WAV
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
        
        zip_size = os.path.getsize(zip_path)
        zip_size_mb = zip_size / 1024 / 1024
        print(f"\nZIP file created: {zip_size_mb:.2f} MB")
        
        # Generate unique object key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        job_id = event.get("id", "unknown")[:8]
        object_key = f"Spleeter/{timestamp}_{job_id}.zip"
        
        # Upload to S3
        expire_seconds = expire_hours * 3600
        s3_info = upload_to_s3(zip_path, bucket_name, object_key, expire_seconds)
        
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
            "download_url": s3_info["url"],
            "s3_key": s3_info["key"],
            "s3_bucket": s3_info["bucket"],
            "expires_at": s3_info["expires_at"],
            "format": output_format,
            "bitrate": bitrate if output_format == "mp3" else "N/A",
            "stems": stems,
            "size_mb": s3_info["size_mb"],
            "files": file_list,
            "instructions": "Download the ZIP file from download_url before it expires"
        }
    
    except Exception as e:
        print("=" * 60)
        print(f"ERROR: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    print("Starting RunPod Spleeter serverless handler with S3 storage...")
    print("Supported stems: 2, 4, 5")
    print("Default: 5 stems (includes piano separation)")
    print("Storage: S3 with presigned URLs")
    runpod.serverless.start({"handler": handler})

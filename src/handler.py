import runpod
import base64
import tempfile
import os
import zipfile
from predict import separate_audio

def handler(event):
    """
    RunPod Serverless Entry
    Expected input:
    {
        "input": {
            "audio_base64": "<base64 audio>",
            "stems": 2  // 2, 4, or 5 stems
        }
    }
    """
    try:
        print("Received request")
        audio_b64 = event["input"]["audio_base64"]
        stems = event["input"].get("stems", 2)  # default 2 stems
        
        audio_bytes = base64.b64decode(audio_b64)
        print(f"Decoded audio: {len(audio_bytes)} bytes, stems: {stems}")

        # Save uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            audio_path = f.name
        
        print(f"Saved audio to {audio_path}")

        # Separate audio
        output_dir = separate_audio(audio_path, stems)
        
        # Zip all output files
        zip_path = tempfile.mktemp(suffix=".zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zipf.write(file_path, arcname)
        
        # Convert ZIP to base64
        with open(zip_path, "rb") as f:
            zip_b64 = base64.b64encode(f.read()).decode()
        
        # Cleanup
        os.unlink(audio_path)
        os.unlink(zip_path)
        
        print("Request completed successfully")
        return {"zip_base64": zip_b64}
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    print("Starting RunPod serverless handler...")
    runpod.serverless.start({"handler": handler})

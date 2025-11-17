import demucs.separate
import torch
import torchaudio
import tempfile
import os

_model = None

def get_model():
    """加载 Demucs 模型"""
    global _model
    if _model is None:
        print("Loading Demucs model...")
        from demucs.pretrained import get_model
        _model = get_model('htdemucs')
        _model.cuda()
        print("Model loaded on GPU!")
    return _model

def separate_audio(audio_path: str, stems: int = 2):
    """
    Separate audio using Demucs
    stems: 2 means vocals + accompaniment (other stems will be mixed)
    """
    print(f"Starting Demucs separation")
    
    # Load audio
    wav, sr = torchaudio.load(audio_path)
    wav = wav.cuda()
    
    # Get model
    model = get_model()
    
    # Separate
    with torch.no_grad():
        sources = demucs.apply.apply_model(
            model, 
            wav[None], 
            device='cuda'
        )[0]
    
    # Output directory
    output_dir = tempfile.mkdtemp()
    
    # Save separated tracks
    # htdemucs outputs: drums, bass, other, vocals
    source_names = ['drums', 'bass', 'other', 'vocals']
    
    for i, name in enumerate(source_names):
        output_path = os.path.join(output_dir, f"{name}.wav")
        torchaudio.save(output_path, sources[i].cpu(), sr)
        print(f"Saved {name} to {output_path}")
    
    # If 2 stems requested, mix non-vocal stems
    if stems == 2:
        accompaniment = sources[0] + sources[1] + sources[2]  # drums + bass + other
        acc_path = os.path.join(output_dir, "accompaniment.wav")
        torchaudio.save(acc_path, accompaniment.cpu(), sr)
        print(f"Saved accompaniment to {acc_path}")
    
    return output_dir

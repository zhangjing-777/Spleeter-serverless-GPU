from spleeter.separator import Separator
import tempfile
import os

# Global separator instances
_separators = {}

def get_separator(stems=2):
    """获取或创建分离器实例"""
    global _separators
    if stems not in _separators:
        print(f"Loading Spleeter {stems}-stems model...")
        _separators[stems] = Separator(f'spleeter:{stems}stems')
        print(f"Model loaded successfully!")
    return _separators[stems]

def separate_audio(audio_path: str, stems: int = 2):
    """
    Separate audio into stems
    stems: 2 (vocals/accompaniment), 4 (vocals/drums/bass/other), 5 (vocals/drums/bass/piano/other)
    """
    print(f"Starting separation with {stems} stems")
    
    # Get separator
    separator = get_separator(stems)
    
    # Output directory
    output_dir = tempfile.mkdtemp()
    
    # Run separation
    separator.separate_to_file(audio_path, output_dir)
    
    print(f"Separation complete, outputs in {output_dir}")
    return output_dir

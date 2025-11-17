from spleeter.separator import Separator
import tempfile
import os
import shutil

# Global separator instances
_separators = {}

def get_separator(stems=2):
    """获取或创建分离器实例"""
    global _separators
    if stems not in _separators:
        print(f"Loading Spleeter {stems}-stems model...")
        try:
            _separators[stems] = Separator(
                f'spleeter:{stems}stems',
                multiprocess=False
            )
            print(f"Model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    return _separators[stems]

def separate_audio(audio_path: str, stems: int = 2):
    """
    Separate audio into stems
    stems: 2 (vocals/accompaniment), 4 (vocals/drums/bass/other), 5 (vocals/drums/bass/piano/other)
    """
    print(f"Starting separation with {stems} stems")
    
    if stems not in [2, 4, 5]:
        raise ValueError(f"Invalid stems value: {stems}. Must be 2, 4, or 5.")
    
    # Get separator
    separator = get_separator(stems)
    
    # Output directory
    output_dir = tempfile.mkdtemp()
    
    try:
        # Run separation
        print(f"Separating audio file: {audio_path}")
        separator.separate_to_file(
            audio_path, 
            output_dir,
            codec='wav'
        )
        
        print(f"Separation complete, outputs in {output_dir}")
        
        # Spleeter creates a subdirectory with the audio filename
        # Find the actual output directory
        subdirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
        if subdirs:
            actual_output_dir = os.path.join(output_dir, subdirs[0])
        else:
            actual_output_dir = output_dir
        
        # List output files
        output_files = []
        for root, dirs, files in os.walk(actual_output_dir):
            for file in files:
                if file.endswith('.wav'):
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    print(f"Output file: {file} ({file_size / 1024:.2f} KB)")
                    output_files.append(file_path)
        
        return actual_output_dir
    
    except Exception as e:
        print(f"Error during separation: {e}")
        # Cleanup on error
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        raise

import mlx_whisper
import time
from pathlib import Path

AUDIO_FILE = "tools/whisperx/audio/test_60s.WAV"

def test_mlx_whisper_turbo():
    if not Path(AUDIO_FILE).exists():
        print(f"File not found: {AUDIO_FILE}")
        return

    print(f"Transcribing {AUDIO_FILE} with mlx-whisper (large-v3-turbo)...")
    start_time = time.time()
    
    # mlx-whisper automatically uses the GPU (Metal) on Mac
    result = mlx_whisper.transcribe(
        AUDIO_FILE,
        path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        fp16=True
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n--- Result (Turbo) ---")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Text snippet: {result['text'][:200]}...")
    print("----------------------")

if __name__ == "__main__":
    test_mlx_whisper_turbo()

import os
import subprocess
from pathlib import Path

# ボイスレコーダーのボリューム名
RECORDER_NAME = "NO NAME"
MOUNT_PATH = f"/Volumes/{RECORDER_NAME}"
# ローカルの保存先
LOCAL_AUDIO_DIR = os.path.expanduser("~/VSCode/brain/0_RAW/audio")

def sync_recorder():
    # 1. デバイスの存在確認
    if not os.path.exists(MOUNT_PATH):
        print(f"Recorder '{RECORDER_NAME}' not found.")
        return False

    print(f"Recorder '{RECORDER_NAME}' detected. Starting sync...")
    
    # 2. ローカルディレクトリの作成
    os.makedirs(LOCAL_AUDIO_DIR, exist_ok=True)

    # 3. 差分コピー (rsync)
    # -a: アーカイブモード (属性維持)
    # -v: 詳細表示
    # --ignore-existing: すでにローカルにあるファイルは上書きしない
    # --include=*.WAV: WAVファイルのみ対象
    try:
        subprocess.run([
            "rsync", "-av", "--ignore-existing", 
            "--include=*/", "--include=*.WAV", "--include=*.wav", "--exclude=*",
            f"{MOUNT_PATH}/", f"{LOCAL_AUDIO_DIR}/"
        ], check=True)
        print("\nSync completed successfully.")
        print(f"Files are safely stored in: {LOCAL_AUDIO_DIR}")
        print(f"You can now safely eject '{RECORDER_NAME}'.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during sync: {e}")
        return False

if __name__ == "__main__":
    sync_recorder()

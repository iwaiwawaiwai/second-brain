#!/usr/bin/env python3
"""
音声文字起こしパイプライン

フロー:
  1. レコーダー(NO NAME)からローカルにWAVをコピー（--sync）
  2. MLX Whisperでローカルの未処理WAVを文字起こし
  3. .txt を brain/3_LOGS/transcripts/YYYY-MM/ に保存
  4. 処理済みWAVをGoogle Driveの voice_archive/YYYY-MM-DD/ に移動（Macから削除）

使い方:
  python voice_pipeline.py               # ローカルの未処理WAVを全部処理
  python voice_pipeline.py --sync        # レコーダーからコピーしてから処理
  python voice_pipeline.py path/to/file.wav  # 特定ファイルを処理
"""

import shutil
import sys
from pathlib import Path

# ─── パス設定 ─────────────────────────────────────────────
REPO_ROOT      = Path(__file__).parent.parent.parent        # ~/VSCode
AUDIO_DIR      = REPO_ROOT / "brain" / "0_RAW" / "audio"   # ローカル作業用
TRANSCRIPT_DIR = REPO_ROOT / "brain" / "3_LOGS" / "transcripts"

GDRIVE_ROOT = Path.home() / "Library" / "CloudStorage" / \
              "GoogleDrive-t.iwaiwawaiwai@gmail.com" / "マイドライブ"
ARCHIVE_DIR = GDRIVE_ROOT / "voice_archive"

MLX_MODEL = "mlx-community/whisper-large-v3-turbo"


# ─── 1. レコーダー同期（--sync 時のみ） ──────────────────
def sync_recorder():
    sys.path.insert(0, str(Path(__file__).parent))
    from sync_recorder import sync_recorder as _sync
    return _sync()


# ─── 2. 文字起こし ────────────────────────────────────────
def transcribe(wav_path: Path) -> str:
    import mlx_whisper
    print(f"[transcribe] {wav_path.name} ...")
    result = mlx_whisper.transcribe(
        str(wav_path),
        path_or_hf_repo=MLX_MODEL,
        language="ja",
        condition_on_previous_text=False,  # リピーティング防止
        no_speech_threshold=0.6,           # 無音・ノイズ区間をスキップ
        compression_ratio_threshold=2.4,   # 繰り返し検出で該当セグメントを破棄
    )
    text = result["text"].strip()
    print(f"[transcribe] 完了 ({len(text)} 文字)")
    return text


# ─── 3. テキスト保存 ──────────────────────────────────────
def save_transcript(wav_path: Path, transcript: str) -> Path:
    # brain/3_LOGS/transcripts/YYYY-MM/ に日付別で保存
    month = wav_path.stem[:7]  # "2026-04-01-..." → "2026-04"
    out_dir = TRANSCRIPT_DIR / month
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / wav_path.with_suffix(".txt").name
    out_path.write_text(transcript, encoding="utf-8")
    print(f"[save] {out_path.relative_to(REPO_ROOT)}")
    return out_path


# ─── 4. WAVをGoogle Driveへ移動（Macから削除） ────────────
def archive_wav(wav_path: Path):
    date = wav_path.stem[:10]  # "2026-04-01"
    dest_dir = ARCHIVE_DIR / date
    dest_dir.mkdir(parents=True, exist_ok=True)

    shutil.move(str(wav_path), str(dest_dir / wav_path.name))
    print(f"[archive] {wav_path.name} → GDrive/voice_archive/{date}/")


# ─── メイン処理 ───────────────────────────────────────────
def process_file(wav_path: Path):
    transcript = transcribe(wav_path)
    if not transcript:
        print(f"[warn] 文字起こし結果が空: {wav_path.name}")
        return

    save_transcript(wav_path, transcript)
    archive_wav(wav_path)
    print(f"[done] {wav_path.name} 完了\n")


def main():
    args = sys.argv[1:]

    if "--sync" in args:
        args.remove("--sync")
        print("=== レコーダー同期 ===")
        sync_recorder()

    if args:
        targets = [Path(a) for a in args]
    else:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        wavs = sorted(AUDIO_DIR.glob("*.WAV")) + sorted(AUDIO_DIR.glob("*.wav"))
        # レコーダーのシステムフォルダは除外
        targets = [w for w in wavs if w.is_file()]

    if not targets:
        print(f"処理対象の WAV ファイルが見つかりません: {AUDIO_DIR}")
        return

    print(f"=== 処理対象: {len(targets)} ファイル ===")
    for wav in targets:
        process_file(wav)

    print("=== 完了 ===")
    print("次のステップ: 「文字起こし結果からタスクを抽出して」と Claude Code に伝える")


if __name__ == "__main__":
    main()

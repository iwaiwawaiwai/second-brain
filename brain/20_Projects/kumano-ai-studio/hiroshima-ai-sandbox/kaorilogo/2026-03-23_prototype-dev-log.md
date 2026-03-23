# KAORILOGOプロトタイプ — 開発ログ

作成日: 2026-03-23
ステータス: 開発中（動作確認フェーズ）

---

## 現行プロトタイプの構成

```
/Users/iiwabook/VSCode/kaorilogo-prototype/
├── server.js        ← Node.js + Express + Anthropic SDK（メインロジック）
├── public/
│   └── index.html   ← チャットUI（2カラム：チャット + 推薦パネル）
└── package.json
```

**起動コマンド:**
```bash
cd /Users/iiwabook/VSCode/kaorilogo-prototype
ANTHROPIC_API_KEY="sk-ant-api03-..." node server.js
```
→ ブラウザで `http://localhost:3000` を開く

---

## 旧バージョンの状態

`/Users/iiwabook/VSCode/projects/kaorilogo/kaorilogo-app.py`（Streamlit版）は旧バージョン。
削除するか否かはまだ未決定。現行はNode.js版を使用。

---

## 今日（2026-03-23）の作業内容

### 問題1：Streamlit版が起動しない
- `zsh: command not found: streamlit` エラー
- **原因**: streamlitがインストールされていない
- **結論**: 現行はNode.js版なのでstreamlitは不要

### 問題2：推薦が途中で切れる（JSON破損）
- 13商品すべてのレコメンド文を返そうとして `max_tokens: 1024` を超えた
- JSONが途中で切れて、フォールバック（3件固定）に落ちていた
- **修正内容（server.js）:**
  1. `max_tokens: 1024` → `max_tokens: 2048` に増加
  2. 推薦件数を「全13件」→「**上位5件のみ**」に変更（内部で全商品スコアリング、上位5件だけ出力）

---

## server.js の現在の設定（重要パラメータ）

| 項目 | 値 |
|---|---|
| モデル | claude-sonnet-4-6 |
| max_tokens | 2048 |
| 推薦出力件数 | 上位5件 |
| エージェント構成 | hearing / proposal / closing（自律切替） |

---

## 次回やること（優先順）

- [ ] サーバー再起動して動作確認（推薦が5件で正しく出るか）
- [ ] 旧Streamlit版（kaorilogo-app.py）の削除判断
- [ ] 今日の変更をgitコミット
- [ ] UIの調整（必要であれば）

---

## 参考：関連ノート

- [チャットフロー設計決定事項](2026-03-23_chatflow-design-decisions.md)
- [プロンプト設計](2026-03-23_prompt-design.md)

import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="KAORILOGO アロマコンシェルジュ",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
.profile-panel {
    background: #f8f4f0;
    border-radius: 12px;
    padding: 20px;
    border-left: 4px solid #a8835a;
}
.phase-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: bold;
    margin-bottom: 8px;
}
.phase-listening  { background: #e8f4e8; color: #2d7a2d; }
.phase-proposing  { background: #fff3e0; color: #b36800; }
.phase-closing    { background: #fce4ec; color: #b0003a; }
div.stButton > button {
    height: 60px;
    font-size: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ─── セッション初期化 ────────────────────────────────
if "phase" not in st.session_state:
    st.session_state.phase = "entrance"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "scene" not in st.session_state:
    st.session_state.scene = None
if "agent_phase" not in st.session_state:
    st.session_state.agent_phase = "listening"   # listening / proposing / closing
if "profile" not in st.session_state:
    st.session_state.profile = {}

# ─── フェーズ別システムプロンプト ───────────────────
PROMPTS = {
    "listening": """あなたはKAORILOGO（アロマ空間デザイン会社）の上級コンシェルジュです。

## 役割：傾聴・共感エージェント
お客様の状況を「言い当てる」ことで信頼を得るのが仕事です。

## 会話スタイル
- 返答は1〜2文のみ。絶対に長くしない
- まず共感・共鳴してから1つだけ質問する
- 相手の言葉をそのまま使って返す（ペーシング）
- 「〜で疲れていませんか？」のように状況を先読みして言い当てる
- 専門用語は使わない

## ゴール
場所・気分・目的が揃ったら「香りをご提案してもいいですか？」と確認して終わる。
絶対に自分から提案しない。許可を得てから次のフェーズへ。

## プロファイル抽出（毎回必ず返す）
返答の末尾に必ず以下のJSON blockを含める：
```profile
{"mood": "（読み取った気分・状態、なければnull）", "purpose": "（目的、なければnull）", "keyword": "（印象的なキーワード、なければnull）", "progress": 整数0〜100, "ready_to_propose": false}
```
progressは「香りを提案できる準備の完成度」。場所・気分・目的それぞれ約33%ずつ加算。全部揃いお客様がOKしたら100。
ready_to_proposeは、場所・気分・目的が揃いお客様が提案OKと言ったときだけtrueにする。""",

    "proposing": """あなたはKAORILOGO（アロマ空間デザイン会社）の香り専門家エージェントです。

## 役割：驚き提案エージェント
「予想通りの提案」ではなく、お客様が「そんな使い方があるの？」と感じる提案をします。

## 提案の作り方
1. **本音に直撃** — ヒアリングで引き出した深層ニーズに正面から応える
2. **意外なシーン展開** — 「この香りは実は〜にも使えます」という驚き要素を必ず1つ入れる
   例：「集中したい方にすすめていますが、実は夜の読書タイムにも最高なんです」
3. **断言する** — 「〜なあなたには、〇〇しかありません」という確信を持った語り口
4. **選択肢は最大2つ** — 多すぎると迷わせる。「まずこれ、もし〜なら次にこれ」という順序をつける

## 絶対ルール
- 返答は2〜3文
- 迷いを見せない
- 香りの名前だけでなく、使う場面・感覚を必ず描写する

## ゴール
お客様が「試してみたい」「詳しく聞きたい」と言ったらクロージングフェーズへ移行する。

## プロファイル抽出（毎回必ず返す）
返答の末尾に必ず以下のJSON blockを含める：
```profile
{"proposed_scents": ["提案した香り名"], "surprise_scene": "（意外な使い方として提案したシーン）", "customer_reaction": "（positive/neutral/negative）", "ready_to_close": false}
```
ready_to_closeは、お客様が前向きな反応を示したときだけtrueにする。""",

    "closing": """あなたはKAORILOGO（アロマ空間デザイン会社）のクロージング専門エージェントです。

## 役割：背中を押すエージェント
お客様が一歩踏み出せるよう、自然に・押しつけがましくなく後押しします。

## 会話スタイル
- 返答は1〜2文
- 「まず試してみませんか？」「小さいサイズから始められます」など、ハードルを下げる
- 「今だけ」「あなただけに」という個別感を出す
- 価格や在庫には触れない（デモのため）

## ゴール
お客様に「次のアクション（購入・問い合わせ）」を取ってもらう。

## プロファイル抽出（毎回必ず返す）
返答の末尾に必ず以下のJSON blockを含める：
```profile
{"closing_stage": "（warm/hot）"}
```"""
}

def extract_profile_json(text: str) -> dict:
    """返答からprofile JSONブロックを抽出"""
    match = re.search(r"```profile\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return {}
    return {}

def clean_response(text: str) -> str:
    """profile JSONブロックを除いた表示用テキスト"""
    return re.sub(r"\n?```profile[\s\S]*?```", "", text).strip()

def call_claude(messages, agent_phase: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=PROMPTS[agent_phase],
        messages=messages
    )
    return response.content[0].text

def update_profile_from_json(data: dict):
    """抽出したJSONでsession profileを更新"""
    for k, v in data.items():
        if v is not None and v != "" and v != []:
            st.session_state.profile[k] = v

# ─── ヘッダー ────────────────────────────────────────
st.markdown("## 🌿 KAORILOGO アロマコンシェルジュ")
st.markdown("あなたの気分や場面を教えてください。ぴったりの香りをご提案します。")
st.markdown("---")

col_chat, col_profile = st.columns([3, 2])

with col_chat:

    # ── 入口カード ──────────────────────────────────
    if st.session_state.phase == "entrance":
        st.markdown("#### どんな場所に香りを使いたいですか？")
        st.markdown("")

        c1, c2 = st.columns(2)
        cards = [
            ("🛏️ 自宅・寝室",       "寝室・自宅",     "寝室で使いたいです",             c1),
            ("💼 仕事・在宅ワーク", "在宅ワーク",     "仕事や在宅ワークで使いたいです", c2),
            ("🚪 玄関・リビング",   "玄関・リビング", "玄関やリビングで使いたいです",   c1),
            ("🎁 プレゼント用",     "プレゼント",     "プレゼントとして贈りたいです",   c2),
        ]
        for label, scene, first_msg, col in cards:
            with col:
                if st.button(label, use_container_width=True):
                    st.session_state.scene = scene
                    st.session_state.messages = [{"role": "user", "content": first_msg}]
                    st.session_state.phase = "chat"
                    st.session_state.agent_phase = "listening"
                    st.session_state.profile = {"scene": scene}
                    st.rerun()

        st.markdown("")
        if st.button("✏️ うまく説明できない…自由に話す", use_container_width=True):
            st.session_state.messages = [{"role": "user", "content": "どんな香りが合うかよくわかりません"}]
            st.session_state.phase = "chat"
            st.session_state.agent_phase = "listening"
            st.session_state.profile = {}
            st.rerun()

    # ── チャット画面 ────────────────────────────────
    elif st.session_state.phase == "chat":

        if st.button("← 最初に戻る"):
            st.session_state.phase = "entrance"
            st.session_state.messages = []
            st.session_state.scene = None
            st.session_state.agent_phase = "listening"
            st.session_state.profile = {}
            st.rerun()

        # フェーズバッジ表示
        phase_labels = {
            "listening": ("ヒアリング中", "listening"),
            "proposing":  ("提案中",       "proposing"),
            "closing":    ("クロージング", "closing"),
        }
        label, css = phase_labels[st.session_state.agent_phase]
        st.markdown(
            f'<span class="phase-badge phase-{css}">● {label}</span>',
            unsafe_allow_html=True
        )
        st.markdown(f"**場面：** {st.session_state.scene or '自由入力'}")
        st.markdown("---")

        # 会話履歴表示（表示用テキストを使う）
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg.get("display", msg["content"]))

        # AIが未返答なら生成
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            with st.spinner("考え中…"):
                api_msgs = [{"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages]
                raw_reply = call_claude(api_msgs, st.session_state.agent_phase)

                # プロファイル抽出・更新
                extracted = extract_profile_json(raw_reply)
                update_profile_from_json(extracted)

                # フェーズ自動切り替え
                if st.session_state.agent_phase == "listening" and extracted.get("ready_to_propose"):
                    st.session_state.agent_phase = "proposing"
                elif st.session_state.agent_phase == "proposing" and extracted.get("ready_to_close"):
                    st.session_state.agent_phase = "closing"

                display_reply = clean_response(raw_reply)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": raw_reply,
                    "display": display_reply
                })
            st.rerun()

        # 入力欄
        if inp := st.chat_input("気分や使いたい場面を自由に話しかけてください…"):
            st.session_state.messages.append({"role": "user", "content": inp, "display": inp})
            st.rerun()

# ─── 右：プロファイルパネル ──────────────────────────
with col_profile:
    p = st.session_state.profile
    scene_text    = p.get("scene")          or st.session_state.scene or "—"
    mood_text     = p.get("mood")           or "—"
    purpose_text  = p.get("purpose")        or "—"
    keyword_text  = p.get("keyword")        or "—"
    proposed      = p.get("proposed_scents")
    proposed_text = "、".join(proposed) if proposed else "—"
    surprise_text = p.get("surprise_scene") or "—"
    progress_val  = p.get("progress", 0) if st.session_state.agent_phase == "listening" else None

    phase_color = {"listening": "#2d7a2d", "proposing": "#b36800", "closing": "#b0003a"}
    color = phase_color.get(st.session_state.agent_phase, "#a8835a")

    # 進捗バー（ヒアリング中のみ）
    if progress_val is not None and st.session_state.phase == "chat":
        pct = max(0, min(100, int(progress_val)))
        st.markdown(f"**プロファイル完成度**")
        st.progress(pct / 100, text=f"{pct}% — あと少しで香りが決まります")
        st.markdown("")

    st.markdown(f"""
    <div class="profile-panel">
        <h4 style="color:{color}; margin:0 0 12px 0">📋 あなたの香りプロファイル</h4>
        <div style="margin:6px 0"><b>📍 場所</b>: {scene_text}</div>
        <div style="margin:6px 0"><b>💭 気分・状態</b>: {mood_text}</div>
        <div style="margin:6px 0"><b>🎯 目的</b>: {purpose_text}</div>
        <div style="margin:6px 0"><b>🔑 キーワード</b>: {keyword_text}</div>
        <div style="margin:6px 0"><b>🌸 提案した香り</b>: {proposed_text}</div>
        <div style="margin:6px 0"><b>✨ 意外なシーン</b>: {surprise_text}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.agent_phase != "listening" and p:
        st.markdown("")
        reaction = p.get("customer_reaction", "")
        if reaction == "positive":
            st.success("お客様の反応：前向き ✓")
        elif reaction == "negative":
            st.warning("お客様の反応：迷い中")

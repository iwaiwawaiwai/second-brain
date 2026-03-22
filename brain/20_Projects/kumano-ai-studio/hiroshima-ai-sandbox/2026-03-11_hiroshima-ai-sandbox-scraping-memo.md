# ひろしまAIサンドボックス 課題一覧 スクレイピング手順書

作成日: 2026/3/11
対象サイト: https://hiroshima-ai-sandbox.jp/issue/list/

---

## サイト構造（重要なCSSクラス名）

| 要素 | CSSクラス |
|------|-----------|
| 課題カード（リンク） | `.p-ip-items__link` |
| カードのタイトル | `.p-ip-items__ttl` |
| カードの会社名 | `.p-ip-items__name` |
| ページネーション | `.p-ip-pagination__btn`（1〜14まで） |
| 詳細モーダル本体 | `.p-ip-modal`（`--open`クラスで開いた状態） |
| モーダルのタイトル | `.p-ip-modal__ttl` |
| モーダルの本文 | `.p-ip-modal__content`（課題詳細・会社情報・活用データ等すべて含む） |
| 産業カテゴリタグ | `.p-ip-items__cat span` |
| AIインパクトタグ | `.p-ip-items__tag span` |
| モーダルの閉じる | `.p-ip-modal__close` |

---

## データ取得の流れ

### STEP 1: タイトル・会社名のみ一括取得

1. ページネーションボタン（`.p-ip-pagination__btn`）を順番にクリックしてページ切り替え
2. 各ページの `.p-ip-items__link` 要素を querySelectorAll で全取得
3. 各カードから `.p-ip-items__ttl` と `.p-ip-items__name` のテキストを抽出
4. `window._allIssues` 配列に `{ title, company }` として蓄積
5. 全14ページ完了後、配列に206件が入る（1ページ約15件 × 14ページ）

### STEP 2: 詳細情報の取得

1. ページネーションボタンで各ページへ移動（1500ms待機）
2. 各カード（`.p-ip-items__link`）をクリック
3. モーダルが開くのを待つ（`.p-ip-modal` に `--open` クラスがつくまでポーリング）
4. `.p-ip-modal__content` の innerText が10文字以上になるまで待つ（コンテンツ描画待ち）
   ※ この待機を入れないと空テキストを取得してしまうので必須
5. モーダルから全情報を抽出:
   - タイトル: `.p-ip-modal__ttl`
   - 本文全文: `.p-ip-modal__content` の innerText（省略なし）
   - カテゴリ: `.p-ip-items__cat span`
   - AIインパクト: `.p-ip-items__tag span`
6. `.p-ip-modal__close` ボタンをクリックしてモーダルを閉じる（400ms待機）
7. `window._allDetails` 配列に蓄積

---

## 待機時間の設定（重要）

| タイミング | 待機時間 |
|-----------|---------|
| ページ切り替え後 | 1500ms |
| カードクリック後（モーダル開くまで） | 最大4000msポーリング（100ms間隔） |
| コンテンツ描画待ち | 最大4000msポーリング（150ms間隔）、10文字以上になったらOK |
| モーダルを閉じた後 | 400〜600ms |

> 待機時間が短いとコンテンツが空になる。コンテンツの描画確認が最重要ポイント。

---

## 実行時の問題と対処

**問題:** 一部のカードでコンテンツ取得がタイムアウトする（数件）
**原因:** 連続クリック時にモーダルコンテンツの描画が遅くなる場合がある
**対処:** 1回目の全件スキャン後、ERRORになったもの「だけ」再スキャン（retryTimeout関数）
　　　再スキャン時はページ切り替えコストを避けるため、同一ページ内の件をまとめて処理

---

## 実行スクリプト

### スクリプト1: 全件取得（コンソール実行用）

ブラウザの開発者ツール（F12）→ コンソールタブに貼り付けてEnter

```javascript
window._allDetails = [];
window._scrapeStatus = 'running';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitForModal(t=4000){const s=Date.now();while(Date.now()-s<t){const m=document.querySelector('.p-ip-modal');if(m&&m.classList.contains('--open'))return true;await sleep(100);}return false;}
async function waitForContent(t=4000){const s=Date.now();while(Date.now()-s<t){const m=document.querySelector('.p-ip-modal');if(m&&m.classList.contains('--open')){const c=m.querySelector('.p-ip-modal__content');if(c&&c.innerText.trim().length>10)return true;}await sleep(150);}return false;}
async function waitForClose(t=2000){const s=Date.now();while(Date.now()-s<t){const m=document.querySelector('.p-ip-modal');if(!m||!m.classList.contains('--open'))return true;await sleep(100);}return false;}

function extract(){const m=document.querySelector('.p-ip-modal');if(!m||!m.classList.contains('--open'))return null;return{title:m.querySelector('.p-ip-modal__ttl')?.textContent.trim()||'',fullText:m.querySelector('.p-ip-modal__content')?.innerText||'',categories:Array.from(m.querySelectorAll('.p-ip-items__cat span')).map(s=>s.textContent.trim()),impactTags:Array.from(m.querySelectorAll('.p-ip-items__tag span')).map(s=>s.textContent.trim())};}

async function scrape(){
  const pages=document.querySelectorAll('.p-ip-pagination__btn').length;
  let no=1;
  for(let p=0;p<pages;p++){
    document.querySelectorAll('.p-ip-pagination__btn')[p].click();
    await sleep(1500);
    const cards=document.querySelectorAll('.p-ip-items__link');
    for(let c=0;c<cards.length;c++){
      const cards2=document.querySelectorAll('.p-ip-items__link');
      const t=cards2[c].querySelector('.p-ip-items__ttl')?.textContent.trim()||'';
      const co=cards2[c].querySelector('.p-ip-items__name')?.textContent.trim()||'';
      cards2[c].click();
      await waitForModal();
      const ok=await waitForContent();
      const d=ok?extract():null;
      window._allDetails.push({no,title:d?.title||t,company:co,categories:d?.categories||[],impactTags:d?.impactTags||[],detail:d?.fullText||'ERROR'});
      no++;
      document.querySelector('.p-ip-modal__close')?.click();
      await waitForClose();
      await sleep(400);
    }
  }
  window._scrapeStatus='done';
  console.log('DONE:', window._allDetails.length, 'items');
}
scrape();
```

完了確認: コンソールに `"DONE: 206 items"` と表示されたらOK

---

### スクリプト2: エラー件の再取得（スクリプト1完了後に実行）

```javascript
async function retry(){
  function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
  async function waitForModal(t=4000){const s=Date.now();while(Date.now()-s<t){const m=document.querySelector('.p-ip-modal');if(m&&m.classList.contains('--open'))return true;await sleep(100);}return false;}
  async function waitForContent(t=4000){const s=Date.now();while(Date.now()-s<t){const m=document.querySelector('.p-ip-modal');if(m&&m.classList.contains('--open')){const c=m.querySelector('.p-ip-modal__content');if(c&&c.innerText.trim().length>10)return true;}await sleep(150);}return false;}
  async function waitForClose(t=2000){const s=Date.now();while(Date.now()-s<t){const m=document.querySelector('.p-ip-modal');if(!m||!m.classList.contains('--open'))return true;await sleep(100);}return false;}
  function extract(){const m=document.querySelector('.p-ip-modal');if(!m||!m.classList.contains('--open'))return null;return{title:m.querySelector('.p-ip-modal__ttl')?.textContent.trim()||'',fullText:m.querySelector('.p-ip-modal__content')?.innerText||'',categories:Array.from(m.querySelectorAll('.p-ip-items__cat span')).map(s=>s.textContent.trim()),impactTags:Array.from(m.querySelectorAll('.p-ip-items__tag span')).map(s=>s.textContent.trim())};}

  const errors=window._allDetails.filter(d=>d.detail==='ERROR').map(d=>d.no);
  let curPage=-1;
  for(const no of errors){
    const pi=Math.ceil(no/15)-1,ci=(no-1)%15;
    if(pi!==curPage){document.querySelectorAll('.p-ip-pagination__btn')[pi].click();await sleep(2000);curPage=pi;}
    const cards=document.querySelectorAll('.p-ip-items__link');
    if(ci>=cards.length)continue;
    cards[ci].click();
    await waitForModal();
    const ok=await waitForContent();
    if(ok){const d=extract();if(d){const idx=window._allDetails.findIndex(x=>x.no===no);if(idx!==-1){window._allDetails[idx].detail=d.fullText;window._allDetails[idx].categories=d.categories;window._allDetails[idx].impactTags=d.impactTags;}}}
    document.querySelector('.p-ip-modal__close')?.click();
    await waitForClose();
    await sleep(600);
  }
  console.log('RETRY DONE. Remaining errors:', window._allDetails.filter(d=>d.detail==='ERROR').length);
}
retry();
```

完了確認: `"RETRY DONE. Remaining errors: 0"` を確認してからダウンロード

---

### スクリプト3: テキストファイルとしてダウンロード

```javascript
(function(){
  function fmt(d){return `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n【No.${d.no}】${d.title}\n■  会社名: ${d.company}\n■  産業カテゴリ: ${d.categories.join('・')}\n■  AIインパクト: ${d.impactTags.join('・')}\n■  詳細:\n${d.detail}`;}
  const txt='ひろしまAIサンドボックス 課題一覧\n取得日時: '+new Date().toLocaleString('ja-JP')+'\n総件数: '+window._allDetails.length+'件\n'+'━'.repeat(50)+'\n\n'+window._allDetails.map(fmt).join('\n\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob(['\uFEFF'+txt],{type:'text/plain;charset=utf-8'}));
  a.download='hiroshima_ai_sandbox_issues.txt';
  a.click();
})();
```

---

## 出力ファイル

- ファイル名: `hiroshima_ai_sandbox_issues.txt`
- 文字コード: UTF-8 BOM付き（メモ帳・Excelでも文字化けしない）
- 総文字数: 約20万文字（199,597文字）
- 総件数: 206件

---

## 注意事項

- 全件取得に約15〜20分かかる（スクリプト1+2合計）
- スクリプト実行中はブラウザのタブを閉じないこと
- ページ数・件数が変わっていた場合でも自動的に対応する（全ページを巡回するため）
- 今後課題数が増えた場合はスクリプトをそのまま再実行すればOK（差分取得ではなく全件再取得）

---

## Claudeに依頼する場合

同じ作業を再度Claudeに依頼する場合は:

> 「ひろしまAIサンドボックスの課題一覧ページ（https://hiroshima-ai-sandbox.jp/issue/list/）を開いた状態で、前回と同様に全課題のタイトル・会社名・詳細情報をテキストファイルで取得してほしい。」

と伝えれば同じ手順で実行できます。

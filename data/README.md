<!-- [DEBUG] ============================================================
Agent   : data_explorer
Task    : 国会議事録 API データ取得・サンプル生成
Created : 2026-02-23
Updated : 2026-02-23
[/DEBUG] ============================================================ -->

# データソース

## 国会会議録検索システム API

本実験では、国立国会図書館が提供する国会会議録検索システム API を共通コーパスとして使用します。

### データソース情報

| 項目 | 内容 |
|------|------|
| 提供機関 | 国立国会図書館（NDL） |
| システム名 | 国会会議録検索システム |
| API エンドポイント | `https://kokkai.ndl.go.jp/api/speech` |
| データ範囲 | 第1回国会（1947年5月）以降 |
| 収録対象 | 本会議・委員会・調査会等の会議録 |

### ライセンス・利用規約

- 国会会議録は著作権法上の立法著作物（著作権法第13条）に該当し、著作権の目的とならないものです。
- API の利用にあたっては、国立国会図書館の利用規約に従ってください。
- 参照: [国会会議録検索システム利用規約](https://kokkai.ndl.go.jp/terms/)

### 引用方法

本データを論文・記事等で引用する場合は以下の形式を推奨します。

```
国立国会図書館「国会会議録検索システム」（https://kokkai.ndl.go.jp/）
取得日: YYYY-MM-DD
```

### API パラメータ

| パラメータ | 説明 | デフォルト値 |
|-----------|------|-------------|
| `any` | 全文検索キーワード | - |
| `speaker` | 発言者名 | - |
| `nameOfHouse` | 院名（衆議院/参議院） | - |
| `nameOfMeeting` | 会議名 | - |
| `from` | 開始日（YYYY-MM-DD） | - |
| `until` | 終了日（YYYY-MM-DD） | - |
| `maximumRecords` | 最大取得件数（1-100） | 10 |
| `startRecord` | 取得開始位置 | 1 |
| `recordPacking` | 出力形式（json/xml） | xml |

### レスポンスフィールド

各発言レコード（`speechRecord`）のフィールド:

| フィールド | 型 | 説明 |
|-----------|----|------|
| `speechID` | string | 発言の一意識別子 |
| `issueID` | string | 会議の識別子 |
| `session` | number | 国会回次 |
| `nameOfHouse` | string | 院名 |
| `nameOfMeeting` | string | 会議名 |
| `issue` | string | 号数 |
| `date` | string | 会議日（YYYY-MM-DD） |
| `speechOrder` | number | 発言順序 |
| `speaker` | string | 発言者名 |
| `speakerYomi` | string | 発言者名（読み） |
| `speakerGroup` | string | 所属会派 |
| `speakerPosition` | string | 役職 |
| `speech` | string | 発言内容 |
| `startPage` | number | 開始ページ |
| `speechURL` | string | 発言への URL |
| `meetingURL` | string | 会議録への URL |

## ディレクトリ構造

```
data/
  README.md              # このファイル
  download.py            # データ取得スクリプト
  .gitignore             # corpus/ を除外
  sample/
    kokkai_sample.json   # サンプルデータ 10件（git 管理対象）
  corpus/                # 実験用コーパス 500件以上（git 管理対象外）
    .gitkeep
    kokkai_*.json        # 取得済みデータ
```

## 使用方法

### サンプルデータのみ確認

```bash
cat data/sample/kokkai_sample.json | python -m json.tool | head -50
```

### 全コーパス取得（500件）

```bash
uv run data/download.py
```

または詳細オプション指定:

```bash
uv run data/download.py --total 500 --batch-size 100 --keyword 教育
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--total` | 取得総件数 | 500 |
| `--batch-size` | 1リクエストあたりの件数（最大100） | 100 |
| `--keyword` | 検索キーワード（空白で全件取得） | "" |
| `--output-dir` | 出力ディレクトリ | data/corpus |
| `--skip-existing` | 既存ファイルをスキップ（冪等性） | True |

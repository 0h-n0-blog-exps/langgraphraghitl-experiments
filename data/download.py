#!/usr/bin/env python3
# [DEBUG] ============================================================
# Agent   : data_explorer
# Task    : 国会議事録 API データ取得・サンプル生成
# Created : 2026-02-23
# Updated : 2026-02-23
# [/DEBUG] ===========================================================

# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
#   "tqdm>=4.66.0",
# ]
# ///

"""
国会会議録検索システム API データ取得スクリプト

国立国会図書館が提供する国会会議録検索システム API から発言データを
非同期で取得し、ローカルに保存します。

Usage:
    uv run data/download.py
    uv run data/download.py --total 500 --batch-size 100 --keyword 教育

API Reference:
    https://kokkai.ndl.go.jp/api/speech
"""

import argparse
import asyncio
import json
import logging
import math
import random
from pathlib import Path
from typing import Any

import httpx
from tqdm import tqdm


# -----------------------------------------------------------------------
# 定数
# -----------------------------------------------------------------------
API_BASE_URL = "https://kokkai.ndl.go.jp/api/speech"
DEFAULT_TOTAL = 500
DEFAULT_BATCH_SIZE = 100
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "corpus"
SAMPLE_DIR = Path(__file__).parent / "sample"
SAMPLE_FILE = SAMPLE_DIR / "kokkai_sample.json"
TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 指数バックオフの基底秒数

# API は検索条件が必須。日付範囲で全件取得する
# 第1回国会（1947年）以降の全データを対象とするデフォルト範囲
DEFAULT_FROM_DATE = "1947-01-01"
DEFAULT_UNTIL_DATE = "2026-12-31"


# -----------------------------------------------------------------------
# ロギング設定（構造化JSON形式）
# -----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='{"event": "%(message)s", "level": "%(levelname)s", "ts": "%(asctime)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# 型エイリアス
# -----------------------------------------------------------------------
SpeechRecord = dict[str, Any]
ApiResponse = dict[str, Any]


# -----------------------------------------------------------------------
# コア関数
# -----------------------------------------------------------------------

async def fetch_speeches(
    client: httpx.AsyncClient,
    start_record: int,
    maximum_records: int,
    keyword: str = "",
    from_date: str = DEFAULT_FROM_DATE,
    until_date: str = DEFAULT_UNTIL_DATE,
) -> ApiResponse:
    """
    国会会議録 API から発言データを取得する。

    指数バックオフ付きリトライを最大 MAX_RETRIES 回実施する。

    Note:
        国会会議録 API は検索条件が必須です。キーワードが空の場合は
        from/until 日付範囲で全件取得します。

    Args:
        client: 共有 httpx.AsyncClient インスタンス
        start_record: 取得開始位置（1-indexed）
        maximum_records: 取得件数（最大100）
        keyword: 全文検索キーワード（空文字列で日付範囲指定に切り替え）
        from_date: 取得開始日（YYYY-MM-DD 形式、keyword 空の場合に使用）
        until_date: 取得終了日（YYYY-MM-DD 形式、keyword 空の場合に使用）

    Returns:
        API レスポンスの dict（numberOfRecords, speechRecord 等を含む）

    Raises:
        httpx.HTTPStatusError: HTTP エラーが MAX_RETRIES 回を超えた場合
        httpx.TimeoutException: タイムアウトが MAX_RETRIES 回を超えた場合
    """
    params: dict[str, str | int] = {
        "maximumRecords": maximum_records,
        "startRecord": start_record,
        "recordPacking": "json",
    }
    if keyword:
        params["any"] = keyword
    else:
        # API は検索条件が必須のため、日付範囲で代替する
        params["from"] = from_date
        params["until"] = until_date

    last_exception: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.get(API_BASE_URL, params=params)
            response.raise_for_status()
            data: ApiResponse = response.json()
            logger.info(
                f"fetch ok start={start_record} count={maximum_records} attempt={attempt}"
            )
            return data

        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as exc:
            last_exception = exc
            if attempt < MAX_RETRIES - 1:
                # 指数バックオフ + ジッタ
                delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(
                    f"retry start={start_record} attempt={attempt + 1}/{MAX_RETRIES} "
                    f"delay={delay:.2f}s error={exc}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"failed start={start_record} all_retries_exhausted error={exc}"
                )

    raise last_exception  # type: ignore[misc]


def build_output_path(output_dir: Path, start_record: int) -> Path:
    """
    出力ファイルパスを構築する。

    Args:
        output_dir: 出力ディレクトリ
        start_record: バッチの開始レコード位置

    Returns:
        出力ファイルの Path オブジェクト
    """
    return output_dir / f"kokkai_{start_record:06d}.json"


async def download_corpus(
    total: int = DEFAULT_TOTAL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    keyword: str = "",
    from_date: str = DEFAULT_FROM_DATE,
    until_date: str = DEFAULT_UNTIL_DATE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    skip_existing: bool = True,
) -> list[SpeechRecord]:
    """
    国会会議録データを非同期で一括取得してファイルに保存する。

    冪等性: skip_existing=True の場合、既存ファイルがあればスキップする。
    サンプル: 最初の10件を data/sample/kokkai_sample.json に保存する。

    Args:
        total: 取得総件数
        batch_size: 1リクエストあたりの取得件数（最大100）
        keyword: 全文検索キーワード（空文字列で日付範囲指定に切り替え）
        from_date: 取得開始日（YYYY-MM-DD、keyword 空の場合に使用）
        until_date: 取得終了日（YYYY-MM-DD、keyword 空の場合に使用）
        output_dir: コーパス出力ディレクトリ
        skip_existing: 既存ファイルをスキップするか（冪等性）

    Returns:
        取得した全 SpeechRecord のリスト
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    # バッチ分割
    batch_starts = list(range(1, total + 1, batch_size))
    num_batches = len(batch_starts)

    logger.info(f"download_start total={total} batch_size={batch_size} batches={num_batches}")

    all_records: list[SpeechRecord] = []
    sample_saved = False

    timeout = httpx.Timeout(TIMEOUT_SECONDS, connect=10.0)

    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": "langgraphraghitl-experiments/1.0 (research; github.com/0h-n0-blog-exps)"},
        follow_redirects=True,
    ) as client:
        with tqdm(total=num_batches, desc="Downloading", unit="batch") as pbar:
            for start_record in batch_starts:
                out_path = build_output_path(output_dir, start_record)

                # 冪等性チェック: 既存ファイルがあればスキップ
                if skip_existing and out_path.exists():
                    logger.info(f"skip_existing path={out_path}")
                    # 既存ファイルからレコードを読み込む
                    with out_path.open(encoding="utf-8") as f:
                        cached: ApiResponse = json.load(f)
                    records = cached.get("speechRecord", [])
                    all_records.extend(records)
                    pbar.update(1)
                    pbar.set_postfix({"records": len(all_records)})

                    # サンプル保存（最初のバッチのみ）
                    if not sample_saved and all_records:
                        _save_sample(all_records[:10])
                        sample_saved = True
                    continue

                # API から取得
                actual_batch = min(batch_size, total - start_record + 1)
                response_data = await fetch_speeches(
                    client, start_record, actual_batch, keyword, from_date, until_date
                )

                records: list[SpeechRecord] = response_data.get("speechRecord", [])
                all_records.extend(records)

                # バッチファイルを保存
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump(response_data, f, ensure_ascii=False, indent=2)

                logger.info(f"saved path={out_path} records={len(records)}")
                pbar.update(1)
                pbar.set_postfix({"records": len(all_records)})

                # サンプル保存（最初のバッチのみ）
                if not sample_saved and records:
                    _save_sample(records[:10])
                    sample_saved = True

                # API レートリミットへの配慮
                await asyncio.sleep(0.3)

    logger.info(f"download_complete total_records={len(all_records)}")
    return all_records


def _save_sample(records: list[SpeechRecord]) -> None:
    """
    最初の10件のレコードをサンプルファイルに保存する。

    Args:
        records: 保存する SpeechRecord のリスト（最大10件）
    """
    sample_records = records[:10]
    sample_data = {
        "description": "国会会議録検索システム API サンプルデータ（10件）",
        "source": "https://kokkai.ndl.go.jp/api/speech",
        "license": "著作権法第13条（立法著作物のため著作権対象外）",
        "numberOfSamples": len(sample_records),
        "speechRecord": sample_records,
    }
    with SAMPLE_FILE.open("w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    logger.info(f"sample_saved path={SAMPLE_FILE} count={len(sample_records)}")


# -----------------------------------------------------------------------
# エントリーポイント
# -----------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser(
        description="国会会議録 API からデータを取得するスクリプト",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--total",
        type=int,
        default=DEFAULT_TOTAL,
        help="取得総件数",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="1リクエストあたりの取得件数（最大100）",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default="",
        help="全文検索キーワード（空白で日付範囲指定に切り替え）",
    )
    parser.add_argument(
        "--from-date",
        type=str,
        default=DEFAULT_FROM_DATE,
        help="取得開始日 YYYY-MM-DD（--keyword 未指定時のみ有効）",
    )
    parser.add_argument(
        "--until-date",
        type=str,
        default=DEFAULT_UNTIL_DATE,
        help="取得終了日 YYYY-MM-DD（--keyword 未指定時のみ有効）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="コーパス出力ディレクトリ",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        default=False,
        help="既存ファイルを再取得する（冪等性を無効化）",
    )
    return parser.parse_args()


async def main() -> None:
    """メインエントリーポイント。"""
    args = parse_args()

    batch_size = min(args.batch_size, 100)  # API 上限は 100
    if batch_size != args.batch_size:
        logger.warning(f"batch_size clamped to 100 (was {args.batch_size})")

    records = await download_corpus(
        total=args.total,
        batch_size=batch_size,
        keyword=args.keyword,
        from_date=args.from_date,
        until_date=args.until_date,
        output_dir=args.output_dir,
        skip_existing=not args.no_skip_existing,
    )
    print(f"\n取得完了: {len(records)} 件のレコードを保存しました")
    print(f"サンプルファイル: {SAMPLE_FILE}")
    print(f"コーパスディレクトリ: {args.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())

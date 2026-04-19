import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from datetime import datetime, timedelta

# =========================
# ▼初回のみ使う開始日
# CSVが存在しない時だけ使われる
# =========================
INITIAL_START_DATE = "20160401"

# 戸田
JCD = "02"

# 保存先
FILE_PATH = "toda_all.csv"

# アクセス用ヘッダー
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.boatrace.jp/"
}


def date_range(start: str, end: str):
    """開始日から終了日までの日付を YYYYMMDD で返す"""
    start_dt = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")

    while start_dt <= end_dt:
        yield start_dt.strftime("%Y%m%d")
        start_dt += timedelta(days=1)


def load_existing_csv(file_path: str) -> pd.DataFrame:
    """既存CSVを読み込む。なければ空DataFrameを返す"""
    if os.path.exists(file_path):
        try:
            df_existing = pd.read_csv(file_path, encoding="utf-8-sig")
            print(f"既存CSV読込: {len(df_existing)}件")
            return df_existing
        except Exception as e:
            print(f"既存CSVの読込に失敗: {e}")
            return pd.DataFrame(columns=["日付", "レース", "着順", "枠番", "選手番号"])

    return pd.DataFrame(columns=["日付", "レース", "着順", "枠番", "選手番号"])


def get_start_date(df_existing: pd.DataFrame) -> str:
    """
    既存CSVがあれば最新日付の次の日を返す
    なければ INITIAL_START_DATE を返す
    """
    if df_existing.empty or "日付" not in df_existing.columns:
        return INITIAL_START_DATE

    try:
        latest_date = pd.to_datetime(df_existing["日付"].astype(str), format="%Y%m%d", errors="coerce").max()

        if pd.isna(latest_date):
            return INITIAL_START_DATE

        next_date = latest_date + timedelta(days=1)
        return next_date.strftime("%Y%m%d")

    except Exception as e:
        print(f"開始日取得失敗: {e}")
        return INITIAL_START_DATE


def get_end_date() -> str:
    """終了日は今日"""
    return datetime.today().strftime("%Y%m%d")


def fetch_race_result(session: requests.Session, date: str, rno: int, jcd: str) -> list[dict]:
    """1レース分の結果を取得して辞書リストで返す"""
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={rno}&jcd={jcd}&hd={date}"
    print("アクセス:", url)

    try:
        res = session.get(url, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"通信失敗 → スキップ ({e})")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")

    race_data = []

    for row in rows:
        cols = [c.text.strip() for c in row.find_all("td")]

        if len(cols) == 4 and cols[0].replace(".", "").isdigit():
            try:
                racer_number = int(cols[2].split()[0])

                race_data.append({
                    "日付": date,
                    "レース": rno,
                    "着順": int(cols[0]),
                    "枠番": int(cols[1]),
                    "選手番号": racer_number
                })
            except (ValueError, IndexError):
                continue

    if len(race_data) == 0:
        print("開催なし or データなし")

    return race_data


def save_csv(df_existing: pd.DataFrame, df_new: pd.DataFrame, file_path: str):
    """既存データと新規取得分を結合し、重複削除して保存"""
    if not df_new.empty:
        for col in ["日付", "レース", "着順", "枠番", "選手番号"]:
            if col in df_new.columns:
                df_new[col] = df_new[col].astype(str)

    if not df_existing.empty:
        for col in ["日付", "レース", "着順", "枠番", "選手番号"]:
            if col in df_existing.columns:
                df_existing[col] = df_existing[col].astype(str)

    df_all = pd.concat([df_existing, df_new], ignore_index=True)

    before_dedup = len(df_all)
    df_all = df_all.drop_duplicates(
        subset=["日付", "レース", "着順", "枠番", "選手番号"]
    )
    after_dedup = len(df_all)

    # 型変換して並び替え
    df_all["日付"] = pd.to_datetime(df_all["日付"], format="%Y%m%d", errors="coerce")
    df_all["レース"] = pd.to_numeric(df_all["レース"], errors="coerce")
    df_all["着順"] = pd.to_numeric(df_all["着順"], errors="coerce")
    df_all["枠番"] = pd.to_numeric(df_all["枠番"], errors="coerce")
    df_all["選手番号"] = pd.to_numeric(df_all["選手番号"], errors="coerce")

    df_all = df_all.sort_values(by=["日付", "レース", "着順", "枠番"]).reset_index(drop=True)

    # 保存前に日付を文字列に戻す
    df_all["日付"] = df_all["日付"].dt.strftime("%Y%m%d")

    df_all.to_csv(file_path, index=False, encoding="utf-8-sig")

    print(f"重複削除前: {before_dedup}件")
    print(f"重複削除後: {after_dedup}件")
    print(f"保存完了: {file_path}")


def main():
    df_existing = load_existing_csv(FILE_PATH)

    start_date = get_start_date(df_existing)
    end_date = get_end_date()

    print(f"開始日: {start_date}")
    print(f"終了日: {end_date}")

    # すでに最新なら何もしない
    if start_date > end_date:
        print("すでに最新です。更新不要")
        return

    session = requests.Session()
    session.headers.update(HEADERS)

    all_data = []

    for date in date_range(start_date, end_date):
        print(f"\n===== {date} =====")

        for rno in range(1, 13):
            race_data = fetch_race_result(session, date, rno, JCD)
            all_data.extend(race_data)

            # アクセス間隔
            time.sleep(random.uniform(1.5, 3.0))

        # 日ごとの休憩
        time.sleep(5)

    df_new = pd.DataFrame(all_data)

    print(f"\n今回取得件数: {len(df_new)}")

    if df_new.empty:
        print("新規取得データなし。処理終了")
        return

    save_csv(df_existing, df_new, FILE_PATH)


if __name__ == "__main__":
    main()
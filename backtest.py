import os
import sys
import pandas as pd

sys.path.append(os.path.abspath("."))

from analysis.basic_stats import race_player_vs_average

# =========================
# ▼設定
# =========================
CSV_PATH = "toda_all.csv"
USE_RECENT = True
RECENT_N = 20


def trust_label(x):
    if x >= 0.8:
        return "高"
    if x >= 0.5:
        return "中"
    return "低"


def head_confidence(row):
    diff = row["1着率差"]
    trust = row["信頼度"]
    lane_exp = row["この枠の経験数"]

    if diff >= 0.10 and trust == "高" and lane_exp >= 5:
        return "かなり高い"
    if diff >= 0.05 and trust in ["高", "中"] and lane_exp >= 3:
        return "高い"
    if diff >= 0:
        return "普通"
    return "低い"


def risk_flag(row):
    flags = []

    if row["信頼度"] == "低":
        flags.append("データ不足")

    if row["トレンド判定"] == "下降":
        flags.append("調子下降")

    if row["枠平均との差"] < 0:
        flags.append("枠相性弱め")

    if row["この枠の経験数"] <= 1:
        flags.append("枠実績ほぼ参考外")
    elif row["この枠の経験数"] <= 3:
        flags.append("枠経験少なめ")

    return " / ".join(flags) if flags else "なし"


def rival_pressure(second_score):
    if second_score >= 1.35:
        return "強い"
    if second_score >= 0.75:
        return "普通"
    return "弱い"


def race_judge_head(df_result):
    top = df_result.iloc[0]
    second = df_result.iloc[1]

    diff = top["頭スコア"] - second["頭スコア"]

    if top["頭確度"] == "低い" or diff < 0.08:
        return "見"

    if top["頭確度"] in ["かなり高い", "高い"] and diff >= 0.20:
        return "買い"

    return "注意"


def summarize_hits(df_source: pd.DataFrame, group_col: str) -> pd.DataFrame:
    summary = (
        df_source.groupby(group_col)
        .agg({
            "1頭的中": ["count", "sum", "mean"],
            "2頭的中": ["sum", "mean"],
            "3頭的中": ["sum", "mean"],
        })
        .reset_index()
    )

    summary.columns = [
        group_col,
        "レース数",
        "1頭的中数", "1頭的中率",
        "2頭的中数", "2頭的中率",
        "3頭的中数", "3頭的中率",
    ]

    summary["1頭的中率"] = summary["1頭的中率"] * 100
    summary["2頭的中率"] = summary["2頭的中率"] * 100
    summary["3頭的中率"] = summary["3頭的中率"] * 100

    return summary


def score_one_race(df_all: pd.DataFrame, race_df: pd.DataFrame):
    race_df = race_df.sort_values("枠番").copy()

    if len(race_df) != 6:
        return None

    lanes = race_df["枠番"].astype(int).tolist()
    player_ids = race_df["選手番号"].astype(int).tolist()

    if sorted(lanes) != [1, 2, 3, 4, 5, 6]:
        return None

    results = race_player_vs_average(
        df_all,
        player_ids,
        lanes,
        recent_n=RECENT_N,
        use_recent=USE_RECENT
    )

    df_result = pd.DataFrame(results)

    if len(df_result) != 6:
        return None

    if USE_RECENT and "当該枠重み付き1着率" in df_result.columns:
        df_result["この枠での1着率"] = df_result["当該枠重み付き1着率"]
    else:
        df_result["この枠での1着率"] = df_result["当該枠1着率"]

    df_result["信頼度"] = df_result["信頼性スコア"].apply(trust_label)
    df_result["枠平均1着率"] = df_result["全体1着率"]
    df_result["この枠の経験数"] = df_result["当該枠出走数"]
    df_result["直近傾向"] = df_result["トレンド判定"]

    df_result["頭スコア"] = (
        df_result["1着率差"] * 2.8
        + df_result["信頼性スコア"] * 1.5
        + df_result["直近トレンドスコア"] * 0.7
        + df_result["枠適性スコア"] * 1.3
    )

    df_result = df_result.sort_values(by="頭スコア", ascending=False).reset_index(drop=True)

    marks = ["◎", "○", "▲", "△", "×", "×"]
    df_result["印"] = marks[:len(df_result)]

    df_result["頭確度"] = df_result.apply(head_confidence, axis=1)
    df_result["危険要素"] = df_result.apply(risk_flag, axis=1)

    if len(df_result) < 3:
        return None

    race_eval = race_judge_head(df_result)

    pred_1 = int(df_result.iloc[0]["枠番"])
    pred_2_list = df_result.iloc[:2]["枠番"].astype(int).tolist()
    pred_3_list = df_result.iloc[:3]["枠番"].astype(int).tolist()

    actual_top = race_df[race_df["着順"] == 1]
    if len(actual_top) != 1:
        return None

    actual_lane = int(actual_top.iloc[0]["枠番"])

    hit_top1 = int(pred_1 == actual_lane)
    hit_top2 = int(actual_lane in pred_2_list)
    hit_top3 = int(actual_lane in pred_3_list)

    return {
        "日付": race_df.iloc[0]["日付"],
        "レース": int(race_df.iloc[0]["レース"]),
        "予想1着枠": pred_1,
        "予想2頭": ",".join(map(str, pred_2_list)),
        "予想3頭": ",".join(map(str, pred_3_list)),
        "実際1着枠": actual_lane,
        "1頭的中": hit_top1,
        "2頭的中": hit_top2,
        "3頭的中": hit_top3,
        "レース評価": race_eval,
        "頭確度": df_result.iloc[0]["頭確度"],
        "信頼度": df_result.iloc[0]["信頼度"],
    }


def main():
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    df["日付"] = pd.to_datetime(df["日付"].astype(str), format="%Y%m%d", errors="coerce")
    df["レース"] = pd.to_numeric(df["レース"], errors="coerce")
    df["着順"] = pd.to_numeric(df["着順"], errors="coerce")
    df["枠番"] = pd.to_numeric(df["枠番"], errors="coerce")
    df["選手番号"] = pd.to_numeric(df["選手番号"], errors="coerce")

    df = df.dropna(subset=["日付", "レース", "着順", "枠番", "選手番号"]).copy()
    df = df.sort_values(["日付", "レース", "枠番"]).reset_index(drop=True)

    race_units = df.groupby(["日付", "レース"], sort=True)

    records = []
    total_races = len(race_units)

    print(f"対象レース数: {total_races}")

    for i, ((race_date, race_no), race_df) in enumerate(race_units, start=1):
        result = score_one_race(df, race_df)
        if result is not None:
            records.append(result)

        if i % 500 == 0:
            print(f"{i} / {total_races} レース処理中...")

    bt = pd.DataFrame(records)

    if bt.empty:
        print("検証対象がありません")
        return

    total = len(bt)

    hit_1 = int(bt["1頭的中"].sum())
    hit_2 = int(bt["2頭的中"].sum())
    hit_3 = int(bt["3頭的中"].sum())

    rate_1 = hit_1 / total * 100
    rate_2 = hit_2 / total * 100
    rate_3 = hit_3 / total * 100

    print("\n==============================")
    print("全体 的中率")
    print("==============================")
    print(f"対象レース数: {total}")
    print(f"◎のみ 的中数: {hit_1} / 的中率: {rate_1:.2f}%")
    print(f"◎○    的中数: {hit_2} / 的中率: {rate_2:.2f}%")
    print(f"◎○▲   的中数: {hit_3} / 的中率: {rate_3:.2f}%")

    summary_eval = summarize_hits(bt, "レース評価")
    print("\n==============================")
    print("レース評価別 的中率")
    print("==============================")
    print(summary_eval.to_string(index=False))

    summary_conf = summarize_hits(bt, "頭確度")
    print("\n==============================")
    print("頭確度別 的中率")
    print("==============================")
    print(summary_conf.to_string(index=False))

    summary_trust = summarize_hits(bt, "信頼度")
    print("\n==============================")
    print("信頼度別 的中率")
    print("==============================")
    print(summary_trust.to_string(index=False))

    bt_save = bt.copy()
    bt_save["日付"] = bt_save["日付"].dt.strftime("%Y%m%d")

    bt_save.to_csv("backtest_results.csv", index=False, encoding="utf-8-sig")
    summary_eval.to_csv("backtest_summary_eval.csv", index=False, encoding="utf-8-sig")
    summary_conf.to_csv("backtest_summary_conf.csv", index=False, encoding="utf-8-sig")
    summary_trust.to_csv("backtest_summary_trust.csv", index=False, encoding="utf-8-sig")

    print("\n保存完了:")
    print("- backtest_results.csv")
    print("- backtest_summary_eval.csv")
    print("- backtest_summary_conf.csv")
    print("- backtest_summary_trust.csv")


if __name__ == "__main__":
    main()
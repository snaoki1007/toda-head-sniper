import pandas as pd
import numpy as np


def _weighted_win_rate(series_bool):
    """
    新しいレースほど重みを高くした1着率
    古い順に並んだ series_bool を想定
    """
    n = len(series_bool)
    if n == 0:
        return 0.0

    weights = np.arange(1, n + 1, dtype=float)
    values = series_bool.astype(float).to_numpy()
    return float(np.average(values, weights=weights))


def _weighted_avg_rank(series_rank):
    """
    新しいレースほど重みを高くした平均着順
    古い順に並んだ series_rank を想定
    """
    n = len(series_rank)
    if n == 0:
        return 0.0

    weights = np.arange(1, n + 1, dtype=float)
    values = series_rank.astype(float).to_numpy()
    return float(np.average(values, weights=weights))


def race_player_vs_average(df, player_ids, lanes, recent_n=20, use_recent=True):
    results = []

    # =========================
    # ▼前処理
    # =========================
    df = df.copy()
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df["着順"] = pd.to_numeric(df["着順"], errors="coerce")
    df["枠番"] = pd.to_numeric(df["枠番"], errors="coerce")
    df["選手番号"] = pd.to_numeric(df["選手番号"], errors="coerce")

    df = df.dropna(subset=["日付", "着順", "枠番", "選手番号"])

    # =========================
    # ▼全体統計
    # =========================
    total_races_all = len(df)
    unique_players = df["選手番号"].nunique()
    avg_races_per_player = total_races_all / unique_players if unique_players > 0 else 0

    overall_avg_rank = df["着順"].mean() if total_races_all > 0 else 0

    # 枠別全体1着率
    win_all = df[df["着順"] == 1].groupby("枠番").size()
    total_all = df.groupby("枠番").size()
    lane_avg_rate = (win_all / total_all).fillna(0)

    # 枠別全体平均着順
    lane_avg_rank = df.groupby("枠番")["着順"].mean()

    # =========================
    # ▼選手ごと処理
    # =========================
    for player_id, lane in zip(player_ids, lanes):
        df_player_base = (
            df[df["選手番号"] == player_id]
            .sort_values("日付")
            .copy()
        )

        if len(df_player_base) == 0:
            results.append({
                "選手番号": int(player_id),
                "枠番": int(lane),
                "1着率": 0.0,
                "重み付き1着率": 0.0,
                "全体1着率": round(float(lane_avg_rate.get(lane, 0)), 3),
                "平均着順": 0.0,
                "重み付き平均着順": 0.0,
                "全体平均着順": round(float(overall_avg_rank), 2),
                "出走数": 0,
                "平均出走数": int(avg_races_per_player),

                "着順標準偏差": 0.0,
                "安定性スコア": 0.0,
                "信頼性スコア": 0.0,

                "1着率差": 0.0,
                "平均着順差": 0.0,
                "相対比較スコア": 0.0,

                "前半平均着順": 0.0,
                "後半平均着順": 0.0,
                "トレンド差": 0.0,
                "トレンド判定": "データ不足",
                "直近トレンドスコア": 0.0,

                "当該枠出走数": 0,
                "当該枠1着率": 0.0,
                "当該枠重み付き1着率": 0.0,
                "枠平均との差": 0.0,
                "枠適性スコア": 0.0,

                "分析モード": f"直近{recent_n}走" if use_recent else "全走"
            })
            continue

        # 分析対象
        if use_recent:
            df_player = df_player_base.tail(recent_n).copy()
        else:
            df_player = df_player_base.copy()

        race_count = len(df_player)
        avg_rank = df_player["着順"].mean() if race_count > 0 else 0.0
        weighted_avg_rank = _weighted_avg_rank(df_player["着順"]) if race_count > 0 else 0.0

        # =========================
        # ① 信頼性
        # =========================
        rank_std = df_player["着順"].std() if race_count > 1 else 0.0

        stability_score = max(0.0, 1 - (rank_std / 3.0)) if race_count > 1 else 0.0
        experience_score = min(race_count / 50, 1.0)

        reliability_score = (stability_score * 0.5) + (experience_score * 0.5)

        # =========================
        # ② 相対比較
        # =========================
        win = df_player[df_player["着順"] == 1].groupby("枠番").size()
        total = df_player.groupby("枠番").size()
        rate = (win / total).fillna(0)

        player_win_rate = float(rate.get(lane, 0))
        lane_base = float(lane_avg_rate.get(lane, 0))

        # 今回枠に絞った重み付き1着率
        df_player_lane = df_player[df_player["枠番"] == lane].copy()
        lane_race_count = len(df_player_lane)

        if lane_race_count > 0:
            lane_win_rate_player = float((df_player_lane["着順"] == 1).mean())
            lane_weighted_win_rate = _weighted_win_rate(df_player_lane["着順"] == 1)
        else:
            lane_win_rate_player = 0.0
            lane_weighted_win_rate = 0.0

        # use_recent の時は重み付き1着率を優先
        effective_win_rate = lane_weighted_win_rate if use_recent and lane_race_count > 0 else player_win_rate
        win_rate_diff = effective_win_rate - lane_base

        lane_base_rank = float(lane_avg_rank.get(lane, overall_avg_rank))
        effective_rank = weighted_avg_rank if use_recent else avg_rank
        avg_rank_diff = lane_base_rank - effective_rank  # ＋なら枠平均より良い

        relative_score = (win_rate_diff * 2.3) + (avg_rank_diff * 0.3)

        # =========================
        # ③ 直近トレンド
        # =========================
        trend_score = 0.0
        first_half_avg = 0.0
        second_half_avg = 0.0
        trend_label = "データ不足"

        if race_count >= 6:
            half = race_count // 2
            first_half = df_player.iloc[:half]
            second_half = df_player.iloc[half:]

            first_half_avg = first_half["着順"].mean()
            second_half_avg = second_half["着順"].mean()

            # 着順は低いほど良い
            trend_score = first_half_avg - second_half_avg

            if trend_score >= 0.5:
                trend_label = "上昇"
            elif trend_score <= -0.5:
                trend_label = "下降"
            else:
                trend_label = "横ばい"

        # =========================
        # ④ 展開適性（今回枠との相性）
        # =========================
        lane_fit_diff = lane_weighted_win_rate - lane_base if use_recent else lane_win_rate_player - lane_base

        lane_sample_weight = min(lane_race_count / 10, 1.0)
        lane_fit_score = lane_fit_diff * lane_sample_weight

        results.append({
            "選手番号": int(player_id),
            "枠番": int(lane),

            "1着率": round(player_win_rate, 3),
            "重み付き1着率": round(float(effective_win_rate), 3),
            "全体1着率": round(lane_base, 3),

            "平均着順": round(float(avg_rank), 2),
            "重み付き平均着順": round(float(weighted_avg_rank), 2),
            "全体平均着順": round(float(overall_avg_rank), 2),

            "出走数": int(race_count),
            "平均出走数": int(avg_races_per_player),

            "着順標準偏差": round(float(rank_std), 2),
            "安定性スコア": round(float(stability_score), 3),
            "信頼性スコア": round(float(reliability_score), 3),

            "1着率差": round(float(win_rate_diff), 3),
            "平均着順差": round(float(avg_rank_diff), 2),
            "相対比較スコア": round(float(relative_score), 3),

            "前半平均着順": round(float(first_half_avg), 2),
            "後半平均着順": round(float(second_half_avg), 2),
            "トレンド差": round(float(trend_score), 2),
            "トレンド判定": trend_label,
            "直近トレンドスコア": round(float(trend_score), 3),

            "当該枠出走数": int(lane_race_count),
            "当該枠1着率": round(float(lane_win_rate_player), 3),
            "当該枠重み付き1着率": round(float(lane_weighted_win_rate), 3),
            "枠平均との差": round(float(lane_fit_diff), 3),
            "枠適性スコア": round(float(lane_fit_score), 3),

            "分析モード": f"直近{recent_n}走" if use_recent else "全走"
        })

    return results
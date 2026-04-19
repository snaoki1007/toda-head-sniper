import os
import sys
import pandas as pd
import streamlit as st

sys.path.append(os.path.abspath("."))

from analysis.basic_stats import race_player_vs_average

st.set_page_config(page_title="ヘッドスナイパー", layout="centered")

# =========================
# ▼号艇カラー
# =========================
BOAT_COLORS = {
    1: {"bg": "#ffffff", "text": "#111111", "border": "#d9d9d9"},
    2: {"bg": "#111111", "text": "#ffffff", "border": "#111111"},
    3: {"bg": "#e53935", "text": "#ffffff", "border": "#e53935"},
    4: {"bg": "#1e88e5", "text": "#ffffff", "border": "#1e88e5"},
    5: {"bg": "#fdd835", "text": "#111111", "border": "#fbc02d"},
    6: {"bg": "#43a047", "text": "#ffffff", "border": "#43a047"},
}

# =========================
# ▼CSS
# =========================
st.markdown(
    """
<style>
.main-title {
    font-size: 2.1rem;
    font-weight: 800;
    margin-bottom: 0.1rem;
}
.sub-title {
    color: #666;
    margin-bottom: 1rem;
    font-size: 0.95rem;
}
.mode-box {
    padding: 10px 14px;
    border-radius: 12px;
    background: #f7f7f7;
    border: 1px solid #e8e8e8;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.6;
}
.boat-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 10px;
}
.eval-card {
    padding: 16px;
    border-radius: 16px;
    background: #fafafa;
    border: 1px solid #e8e8e8;
    margin-bottom: 12px;
}
.main-card {
    padding: 20px;
    border-radius: 18px;
    background: #fffdf8;
    border: 2px solid #f0d28a;
    margin-bottom: 12px;
}
.info-chip {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #f1f3f5;
    margin: 4px 6px 4px 0;
    font-size: 0.88rem;
}
.strength-box {
    padding: 10px 12px;
    border-radius: 12px;
    background: #f7fbf7;
    border: 1px solid #dfeee0;
    margin-top: 8px;
    line-height: 1.6;
}
.risk-box {
    padding: 10px 12px;
    border-radius: 12px;
    background: #fff8f8;
    border: 1px solid #f1d8d8;
    margin-top: 8px;
    line-height: 1.6;
}
.conclusion-box {
    padding: 10px 12px;
    border-radius: 12px;
    background: #f7f8ff;
    border: 1px solid #dde2ff;
    margin-top: 8px;
    font-weight: 700;
    line-height: 1.6;
}
.judge-buy {
    padding: 14px 16px;
    border-radius: 14px;
    background: #f4fbf4;
    border: 1px solid #cfe8cf;
    font-weight: 700;
    font-size: 1.02rem;
}
.judge-mid {
    padding: 14px 16px;
    border-radius: 14px;
    background: #fff9f2;
    border: 1px solid #f1dfbf;
    font-weight: 700;
    font-size: 1.02rem;
}
.judge-skip {
    padding: 14px 16px;
    border-radius: 14px;
    background: #fff5f5;
    border: 1px solid #efc9c9;
    font-weight: 700;
    font-size: 1.02rem;
}
.small-note {
    color: #666;
    font-size: 0.9rem;
    margin-top: 6px;
    font-weight: 500;
}
.reference-box {
    padding: 14px 16px;
    border-radius: 14px;
    background: #f8fafc;
    border: 1px solid #dfe7ef;
    line-height: 1.8;
    margin-bottom: 14px;
}
.recommend-box {
    padding: 14px 16px;
    border-radius: 14px;
    background: #f7f8ff;
    border: 1px solid #dde2ff;
    line-height: 1.8;
    margin-bottom: 14px;
    font-weight: 700;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">🎯 ヘッドスナイパー</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">1着候補を狙い撃つ、戸田特化の頭予想アプリ</div>',
    unsafe_allow_html=True,
)

import datetime
import os

if os.path.exists("backtest_summary_eval.csv"):
    file_time = os.path.getmtime("backtest_summary_eval.csv")
    update_time = datetime.datetime.fromtimestamp(file_time)
    st.caption(f"最終更新：{update_time.strftime('%Y-%m-%d %H:%M')}")

# =========================
# ▼データ読込
# =========================
df = pd.read_csv("toda_all.csv")

# 過去参考データ
summary_eval_path = "backtest_summary_eval.csv"
if os.path.exists(summary_eval_path):
    summary_eval_df = pd.read_csv(summary_eval_path, encoding="utf-8-sig")
else:
    summary_eval_df = pd.DataFrame()

st.markdown("### 👇 出走選手入力")

# =========================
# ▼分析モード
# =========================
mode = st.selectbox("分析モード", ["直近N走", "全走"])

recent_n = 20
if mode == "直近N走":
    recent_n = st.slider("直近何走を見る？", 5, 100, 20)

use_recent = mode == "直近N走"

mode_label = f"直近{recent_n}走" if use_recent else "全走"
weight_note = "※直近モードでは新しいレースほど重く評価" if use_recent else "※全走ベースで安定重視"

st.markdown(
    f"""
<div class="mode-box">
分析モード：{mode_label}<br>
<span class="small-note">{weight_note}</span>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# ▼入力UI（2列×3段）
# =========================
player_ids = []
lanes = [1, 2, 3, 4, 5, 6]

for row_start in [0, 2, 4]:
    cols = st.columns(2)
    for j in range(2):
        i = row_start + j
        lane = i + 1
        c = BOAT_COLORS[lane]

        with cols[j]:
            st.markdown(
                f"""
<div style="
    background:{c['bg']};
    color:{c['text']};
    border:1px solid {c['border']};
    border-radius:12px;
    text-align:center;
    font-weight:800;
    padding:10px 0;
    margin-bottom:8px;
">
    {lane}号艇
</div>
""",
                unsafe_allow_html=True,
            )

            pid = st.number_input(
                f"{lane}号艇の選手番号",
                step=1,
                key=i,
                min_value=0,
                label_visibility="collapsed",
            )
            player_ids.append(int(pid))

# =========================
# ▼補助関数
# =========================
def trust_label(x):
    if x >= 0.8:
        return "高"
    if x >= 0.5:
        return "中"
    return "低"


def pct(x):
    return f"{x * 100:.1f}%"


def pt(x):
    sign = "+" if x >= 0 else ""
    return f"{sign}{x * 100:.1f}pt"


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
        return "skip", "見", "頭候補の優位性が弱く、無理に触りづらいレース。"

    if top["頭確度"] in ["かなり高い", "高い"] and diff >= 0.20:
        return "buy", "買い", "上位候補が比較的はっきりしており、勝負しやすいレース。"

    return "mid", "注意", "本命はいるが、対抗との差や不安要素を見ながら判断したいレース。"


def make_strength_text(row):
    strengths = []

    if row["頭確度"] == "かなり高い":
        strengths.append("頭候補としてかなり有力")
    elif row["頭確度"] == "高い":
        strengths.append("頭候補として有力")
    elif row["頭確度"] == "普通":
        strengths.append("頭候補としては平均圏")

    if row["トレンド判定"] == "上昇":
        strengths.append("最近は上向き")

    if row["枠平均との差"] >= 0.10:
        strengths.append("この枠でかなり抜けている")
    elif row["枠平均との差"] >= 0.04:
        strengths.append("この枠で平均以上")

    return " / ".join(strengths) if strengths else "目立つ強みは少なめ"


def make_risk_text(row):
    return row["危険要素"] if row["危険要素"] != "なし" else "なし"


def make_conclusion_text(row):
    if row["頭確度"] == "かなり高い" and row["危険要素"] == "なし":
        return "頭固定候補"
    if row["頭確度"] in ["かなり高い", "高い"]:
        return "頭候補の中心"
    if row["頭確度"] == "普通":
        return "押さえ付きで検討"
    return "頭固定は危険寄り"


def boat_badge(lane):
    c = BOAT_COLORS[lane]
    return f"""<div class="boat-badge" style="background:{c['bg']}; color:{c['text']}; border:1px solid {c['border']};">
{lane}号艇
</div>"""


def render_card(row, main=False, pressure_label=None, compact=False):
    lane = int(row["枠番"])
    badge = boat_badge(lane)
    card_class = "main-card" if main else "eval-card"

    pressure_html = ""
    if pressure_label is not None:
        pressure_html = f'<div class="info-chip">対抗圧：{pressure_label}</div>'

    if compact:
        return f"""<div class="{card_class}">
{badge}
<h3 style="margin:0 0 8px 0;">{row['印']} {lane}号艇</h3>
<p><strong>選手番号</strong>：{int(row['選手番号'])}</p>

<div class="info-chip">頭確度：{row['頭確度']}</div>
<div class="info-chip">信頼度：{row['信頼度']}</div>
<div class="info-chip">直近傾向：{row['直近傾向']}</div>

<p><strong>枠平均との差</strong>：{pt(row['枠平均との差'])}</p>

<div class="strength-box"><strong>強み</strong>：{row['強み']}</div>
<div class="risk-box"><strong>不安</strong>：{row['不安']}</div>
<div class="conclusion-box"><strong>結論</strong>：{row['結論']}</div>
</div>"""

    return f"""<div class="{card_class}">
{badge}
<h3 style="margin:0 0 8px 0;">{row['印']} {lane}号艇</h3>
<p><strong>選手番号</strong>：{int(row['選手番号'])}</p>

<div class="info-chip">頭確度：{row['頭確度']}</div>
<div class="info-chip">信頼度：{row['信頼度']}</div>
<div class="info-chip">直近傾向：{row['直近傾向']}</div>
{pressure_html}

<p><strong>この枠での1着率</strong>：{pct(row['この枠での1着率'])}</p>
<p><strong>枠平均1着率</strong>：{pct(row['枠平均1着率'])}</p>
<p><strong>枠平均との差</strong>：{pt(row['枠平均との差'])}</p>
<p><strong>この枠の経験数</strong>：{int(row['この枠の経験数'])}走</p>

<div class="strength-box"><strong>強み</strong>：{row['強み']}</div>
<div class="risk-box"><strong>不安</strong>：{row['不安']}</div>
<div class="conclusion-box"><strong>結論</strong>：{row['結論']}</div>
</div>"""


def get_reference_rates(summary_df: pd.DataFrame, race_eval_label: str):
    if summary_df.empty:
        return None

    target = summary_df[summary_df["レース評価"] == race_eval_label]
    if target.empty:
        return None

    row = target.iloc[0]
    return {
        "1頭的中率": float(row["1頭的中率"]),
        "2頭的中率": float(row["2頭的中率"]),
        "3頭的中率": float(row["3頭的中率"]),
        "レース数": int(row["レース数"]),
    }


def recommend_heads(race_eval_label: str, top_head_conf: str):
    if race_eval_label == "見":
        return "見寄り", "過去参考でも弱めなので、無理に頭を追わない方が良い。"

    if top_head_conf == "高い":
        return "2頭推奨", "頭確度が高めなので、まずは上位2頭で絞る形が有力。"

    if top_head_conf == "かなり高い":
        return "2頭推奨", "頭候補が強いので、上位2頭中心で考えやすい。"

    return "3頭推奨", "頭確度が普通帯なので、上位3頭まで見た方が安全。"


# =========================
# ▼分析
# =========================
if st.button("🚀 分析する", use_container_width=True):
    if 0 in player_ids:
        st.error("全て入力してください")
    else:
        results = race_player_vs_average(
            df,
            player_ids,
            lanes,
            recent_n=recent_n,
            use_recent=use_recent,
        )

        df_result = pd.DataFrame(results)

        if use_recent:
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
        df_result["順位"] = df_result.index + 1

        marks = ["◎", "○", "▲", "△", "×", "×"]
        df_result["印"] = marks[:len(df_result)]

        df_result["頭確度"] = df_result.apply(head_confidence, axis=1)
        df_result["危険要素"] = df_result.apply(risk_flag, axis=1)
        df_result["強み"] = df_result.apply(make_strength_text, axis=1)
        df_result["不安"] = df_result.apply(make_risk_text, axis=1)
        df_result["結論"] = df_result.apply(make_conclusion_text, axis=1)

        second_score = df_result.iloc[1]["頭スコア"] if len(df_result) > 1 else 0
        pressure_label = rival_pressure(second_score)

        judge_kind, race_eval_label, race_comment = race_judge_head(df_result)

        st.markdown("## 🎯 レース評価")
        judge_class = "judge-buy" if judge_kind == "buy" else ("judge-skip" if judge_kind == "skip" else "judge-mid")
        st.markdown(
            f"""
<div class="{judge_class}">
{race_eval_label}
<div class="small-note">{race_comment}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # ▼今回の頭候補
        top2 = df_result.iloc[:2]["枠番"].astype(int).tolist()
        top3 = df_result.iloc[:3]["枠番"].astype(int).tolist()

        # ▼過去参考
        ref_rates = get_reference_rates(summary_eval_df, race_eval_label)

        if ref_rates is not None:
            st.markdown("## 📈 過去参考")
            st.markdown(
                f"""
<div class="reference-box">
今回のレース評価：<strong>{race_eval_label}</strong><br>
対象レース数：{ref_rates['レース数']}<br>
1頭的中率：{ref_rates['1頭的中率']:.1f}%<br>
2頭的中率：{ref_rates['2頭的中率']:.1f}%<br>
3頭的中率：{ref_rates['3頭的中率']:.1f}%
</div>
""",
                unsafe_allow_html=True,
            )

        # ▼今回の推奨
        recommend_label, recommend_comment = recommend_heads(race_eval_label, df_result.iloc[0]["頭確度"])
        st.markdown("## 🧭 今回の推奨")
        st.markdown(
            f"""
<div class="recommend-box">
頭候補2頭：{top2}<br>
頭候補3頭：{top3}<br>
推奨：{recommend_label}<br>
<span class="small-note">{recommend_comment}</span>
</div>
""",
            unsafe_allow_html=True,
        )

        # ▼本命
        top = df_result.iloc[0]
        st.markdown("## 🏆 本命")
        st.markdown(render_card(top, main=True, pressure_label=pressure_label, compact=False), unsafe_allow_html=True)

        # ▼上位評価
        st.markdown("## 📌 上位評価")
        for i in range(1, min(3, len(df_result))):
            row = df_result.iloc[i]
            st.markdown(render_card(row, compact=True), unsafe_allow_html=True)

        # ▼穴候補
        with st.expander("💡 穴候補を見る"):
            ana_rows = df_result[
                (df_result["順位"] >= 3)
                & (df_result["枠番"] >= 4)
                & (df_result["枠平均との差"] >= 0.03)
                & (df_result["信頼度"] != "低")
                & (df_result["直近傾向"] != "下降")
            ]

            if len(ana_rows) == 0:
                st.write("今回は明確な穴候補なし")
            else:
                for _, row in ana_rows.iterrows():
                    lane = int(row["枠番"])
                    st.markdown(boat_badge(lane), unsafe_allow_html=True)
                    st.markdown(
                        f"""
**{lane}号艇 / 選手番号 {int(row['選手番号'])}**  
- 頭確度：{row['頭確度']}
- 枠平均との差：{pt(row['枠平均との差'])}
- 直近傾向：{row['直近傾向']}
- 強み：{row['強み']}
- 不安：{row['不安']}
- 結論：{row['結論']}
"""
                    )

        # ▼全艇一覧
        with st.expander("📊 全艇一覧を見る"):
            display_df = df_result[
                [
                    "順位",
                    "印",
                    "枠番",
                    "選手番号",
                    "頭確度",
                    "信頼度",
                    "直近傾向",
                    "枠平均との差",
                    "危険要素",
                ]
            ].copy()

            display_df["枠平均との差"] = display_df["枠平均との差"].apply(pt)

            st.dataframe(display_df, use_container_width=True, hide_index=True)
import streamlit as st
import pandas as pd
from datetime import date, datetime

# --- アプリの設定 ---
st.set_page_config(page_title="DQW Stronger Manager", page_icon="⚔️")

st.title("⚔️ DQW 進捗管理マネージャー")
st.caption("今日の積み重ねが、明日の「最強」を作る。")

# --- サイドバー：基本設定 ---
with st.sidebar:
    st.header("🎯 目標設定")
    # 目標期日
    target_date = st.date_input("いつまでに強くなる？", value=date(2026, 4, 30))
    
    st.divider()
    
    st.markdown("### 📝 管理データ")
    # 狙っているこころリスト（ここを書き換えれば自分用にカスタマイズできます）
    default_kokoro_list = [
        {"name": "キラーマジンガ", "type": "黒", "status": False},
        {"name": "ラプソーン", "type": "青", "status": False},
        {"name": "ギュメイ将軍", "type": "赤", "status": False},
        {"name": "覚醒千里行（対象）", "type": "特殊", "status": False},
    ]

# --- メインエリア A：レベリング予実管理（今日のノルマ） ---
st.header("1. レベリング進捗 (今日のノルマ)")

col1, col2 = st.columns(2)

with col1:
    # 現在の状況入力
    current_xp = st.number_input("現在の累計経験値 (万)", min_value=0, value=1000, step=10)
    st.caption("※ステータス画面の数値を入力")

with col2:
    # 目標入力
    target_xp = st.number_input("目標の累計経験値 (万)", min_value=0, value=2000, step=100)
    st.caption("※Lv60なら約◯◯万、等で設定")

# 計算ロジック
today = date.today()
days_left = (target_date - today).days

if days_left <= 0:
    st.error("目標期日が過ぎています！期日を再設定してください。")
else:
    remaining_xp = target_xp - current_xp
    daily_quota = remaining_xp / days_left

    # 結果表示
    st.divider()
    if remaining_xp <= 0:
        st.success("🎉 目標達成です！おめでとうございます！")
    else:
        st.markdown(f"目標まであと **{days_left}日**")
        
        # インパクトのある数字表示
        st.metric(
            label="今日稼ぐべき経験値",
            value=f"{daily_quota:,.1f} 万 EXP",
            delta=f"残り合計: {remaining_xp:,.0f} 万"
        )

        # アドバイス
        if daily_quota > 300:
            st.warning("⚠️ かなりハードな目標です。メタルキャンペーンを活用するか、目標下方修正を検討しましょう。")
        elif daily_quota > 100:
            st.info("🔥 週末に「週末メタルダンジョン」等で稼ぎましょう。")
        else:
            st.success("✅ 無理のないペースです。毎日のウォークで達成可能です。")

# --- メインエリア B：未取得リスト（こころ・コンテンツ） ---
st.header("2. ターゲット討伐リスト (未取得)")
st.info("Sランク未所持のこころや、クリアしていないコンテンツをチェックしましょう。")

# データの保持（簡易的）
if 'kokoro_targets' not in st.session_state:
    st.session_state['kokoro_targets'] = default_kokoro_list

# リスト表示と操作
for index, item in enumerate(st.session_state['kokoro_targets']):
    cols = st.columns([0.1, 0.7, 0.2])
    
    # チェックボックス
    is_done = cols[0].checkbox("", key=f"check_{index}", value=item["status"])
    
    # テキスト表示（完了したら打消し線）
    if is_done:
        cols[1].markdown(f"~~{item['name']}~~")
        st.session_state['kokoro_targets'][index]["status"] = True
    else:
        cols[1].markdown(f"**{item['name']}**")
        st.session_state['kokoro_targets'][index]["status"] = False
        
    # タイプ表示
    cols[2].caption(f"[{item['type']}]")

# 新規追加機能（簡易）
with st.expander("＋ リストに追加する"):
    new_kokoro = st.text_input("追加したいこころ/コンテンツ名")
    new_type = st.selectbox("タイプ", ["赤", "青", "黄", "紫", "緑", "特殊", "コンテンツ"])
    if st.button("追加"):
        if new_kokoro:
            st.session_state['kokoro_targets'].append({"name": new_kokoro, "type": new_type, "status": False})
            st.rerun()

# --- フッター ---
st.divider()
st.caption("Generated for Hitachi IT Consultant via Gemini")

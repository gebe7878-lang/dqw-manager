import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os

# --- 設定: スマホで見やすく ---
st.set_page_config(page_title="DQW Manager", page_icon="🛡️", layout="centered")

# --- データ保存用関数 (CSV) ---
HISTORY_FILE = "dqw_history.csv"

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    else:
        return pd.DataFrame(columns=["date", "task", "done"])

def save_history(df):
    df.to_csv(HISTORY_FILE, index=False)

def toggle_task(task_name):
    # 履歴データの読み込み
    df = load_history()
    today_str = date.today().isoformat()
    
    # 今日の該当タスクのレコードを探す
    mask = (df["date"] == today_str) & (df["task"] == task_name)
    
    if mask.any():
        # 既に記録がある場合は反転させる（True <-> False）
        current_status = df.loc[mask, "done"].values[0]
        df.loc[mask, "done"] = not current_status
    else:
        # 新規作成（チェックした状態にする）
        new_row = pd.DataFrame({"date": [today_str], "task": [task_name], "done": [True]})
        df = pd.concat([df, new_row], ignore_index=True)
    
    save_history(df)

# --- アプリ本体 ---
st.title("🛡️ DQW Manager")

# タブメニュー (下部ナビゲーションの代わりに上部に配置)
tab_daily, tab_level, tab_history, tab_kokoro = st.tabs(["✅ 日課", "📈 育成", "📅 履歴", "🔍 収集"])

# ==========================================
# Tab 1: 日課 (スマホ操作メイン)
# ==========================================
with tab_daily:
    st.subheader("今日の進捗")
    
    # 履歴データの取得
    df_hist = load_history()
    today_str = date.today().isoformat()
    
    # --- 日課リスト定義 ---
    daily_tasks = [
        "デイリークエスト",
        "スラミチメダル回収",
        "カジノコイン回収",
        "CM動画視聴 (ジェム)",
        "自宅キラキラ回収",
        "仲間モンスター世話",
    ]
    
    weekly_tasks = [
        "週末メタルダンジョン",
        "覚醒千里行",
        "ほこら更新/消化",
        "マイレージ確認",
    ]

    # --- UI表示 ---
    # 進捗バーの計算
    today_data = df_hist[df_hist["date"] == today_str]
    # 今日のタスクで、かつDoneになっているものの数
    done_count = sum(1 for t in daily_tasks if not today_data[(today_data["task"] == t) & (today_data["done"] == True)].empty)
    progress = done_count / len(daily_tasks)
    st.progress(progress)
    st.caption(f"達成率: {int(progress * 100)}%")

    st.write("---")
    st.markdown("##### 🌞 毎日やること")
    
    # スマホで押しやすいように、expanderを使わず直接配置
    for task in daily_tasks:
        # 現在の状態を確認
        is_checked = not today_data[(today_data["task"] == task) & (today_data["done"] == True)].empty
        
        # チェックボックス (callbackで状態保存)
        if st.checkbox(task, value=is_checked, key=f"d_{task}"):
            if not is_checked: # False -> True になった時
                toggle_task(task)
                st.rerun()
        else:
            if is_checked: # True -> False になった時
                toggle_task(task)
                st.rerun()

    st.write("---")
    st.markdown("##### 📅 週課 / その他")
    for task in weekly_tasks:
        is_checked = not today_data[(today_data["task"] == task) & (today_data["done"] == True)].empty
        if st.checkbox(task, value=is_checked, key=f"w_{task}"):
             if not is_checked: toggle_task(task); st.rerun()
        else:
             if is_checked: toggle_task(task); st.rerun()

# ==========================================
# Tab 2: 育成 (レベリング)
# ==========================================
with tab_level:
    # 設定をここに移動（サイドバーを開かなくて済むように）
    with st.expander("🎯 目標設定を開く", expanded=False):
        target_date = st.date_input("いつまでに達成？", value=date(2026, 4, 30))
        target_xp = st.number_input("目標経験値 (万)", min_value=0, value=2000, step=100)
    
    st.subheader("📊 今日のノルマ")
    current_xp = st.number_input("現在の経験値 (万)", min_value=0, value=1000, step=10)

    # 計算
    days_left = (target_date - date.today()).days
    if days_left > 0:
        rem_xp = target_xp - current_xp
        quota = rem_xp / days_left
        st.info(f"残り日数: **{days_left}日**")
        st.metric("今日稼ぐ経験値", f"{quota:,.1f} 万", delta=f"残り合計: {rem_xp}万")
        
        if quota > 300:
            st.warning("⚠️ かなりハードです！ウォークモード活用を！")
    else:
        st.success("期日到達！")

# ==========================================
# Tab 3: 履歴 (新機能)
# ==========================================
with tab_history:
    st.subheader("📅 活動記録")
    
    df = load_history()
    if not df.empty:
        # 直近7日間の達成数集計
        df['date_dt'] = pd.to_datetime(df['date']).dt.date
        daily_counts = df[df['done']==True].groupby('date_dt')['task'].count()
        
        st.bar_chart(daily_counts)
        
        st.write("▼ 詳細ログ")
        # 見やすいように直近を上に
        st.dataframe(df[df['done']==True].sort_values('date', ascending=False), use_container_width=True)
        
        # データダウンロード機能
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("履歴をCSVで保存", csv, "dqw_history.csv", "text/csv")
        st.caption("※Cloud版ではアプリが再起動すると履歴が消えることがあります。こまめにダウンロードするか、PCで実行することをお勧めします。")
    else:
        st.info("まだ記録がありません。日課タブでチェックを入れましょう！")

# ==========================================
# Tab 4: 収集 (こころ)
# ==========================================
with tab_kokoro:
    st.subheader("🔍 収集アシスト")
    
    # ボタンを大きく配置
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("📺 YouTube検索", "https://www.youtube.com/results?search_query=ドラクエウォーク+最強こころ+最新", use_container_width=True)
    with col2:
        st.link_button("🛡️ 攻略サイト", "https://walk.gamewith.jp/", use_container_width=True)
        
    st.write("---")
    
    # セッション管理（簡易）
    if 'targets' not in st.session_state:
        st.session_state['targets'] = ["覚醒千里行", "キラーマジンガ"]
        
    st.markdown("##### ほしい物リスト")
    for i, t in enumerate(st.session_state['targets']):
        c1, c2 = st.columns([0.8, 0.2])
        c1.write(f"・{t}")
        if c2.button("×", key=f"del_{i}"):
            st.session_state['targets'].pop(i)
            st.rerun()
            
    with st.form("add"):
        new = st.text_input("追加など")
        if st.form_submit_button("追加", use_container_width=True) and new:
            st.session_state['targets'].append(new)
            st.rerun()

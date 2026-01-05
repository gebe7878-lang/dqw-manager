import streamlit as st
import pandas as pd
import os

# --- 設定: 画面を広く、白く ---
st.set_page_config(page_title="DQW Manager V4", page_icon="🛡️", layout="wide")

# 強制ホワイトモード（簡易適用）
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #ffffff; color: #000000; }
        [data-testid="stSidebar"] { background-color: #f0f2f6; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 関数: データの読み書き (CSV保存機能)
# ==========================================
TASK_FILE = "daily_tasks.csv"
KOKORO_FILE = "kokoro_list.csv"

def load_tasks():
    if os.path.exists(TASK_FILE):
        return pd.read_csv(TASK_FILE)
    else:
        # 初期データ
        return pd.DataFrame([
            {"task": "デイリークエスト", "done": False},
            {"task": "スラミチメダル回収", "done": False},
            {"task": "CM動画視聴", "done": False},
        ])

def save_tasks(df):
    df.to_csv(TASK_FILE, index=False)

def load_kokoro():
    if os.path.exists(KOKORO_FILE):
        return pd.read_csv(KOKORO_FILE)
    else:
        # 初期データ
        return pd.DataFrame([
            {"名前": "キラーマジンガ", "優先度": "高", "目標数": 2, "所持数": 0, "完了": False},
            {"名前": "覚醒千里行対象", "優先度": "中", "目標数": 4, "所持数": 1, "完了": False},
            {"名前": "メタルキング", "優先度": "低", "目標数": 1, "所持数": 1, "完了": True},
        ])

def save_kokoro(df):
    df.to_csv(KOKORO_FILE, index=False)

# ==========================================
# メイン処理
# ==========================================
st.title("🛡️ DQW 進捗マネージャー V4")
st.caption("データは自動保存されます。")

# データ読み込み
if 'tasks_df' not in st.session_state:
    st.session_state['tasks_df'] = load_tasks()
if 'kokoro_df' not in st.session_state:
    st.session_state['kokoro_df'] = load_kokoro()

tab1, tab2, tab3 = st.tabs(["✅ 日課設定", "❤️ こころ管理", "💾 データバックアップ"])

# ==========================================
# Tab 1: 日課 (追加・削除・保存)
# ==========================================
with tab1:
    st.subheader("📝 今日の日課")
    
    # 追加フォーム
    with st.expander("＋ 日課を追加する"):
        with st.form("add_task"):
            new_task = st.text_input("タスク名")
            if st.form_submit_button("追加"):
                if new_task:
                    new_row = pd.DataFrame([{"task": new_task, "done": False}])
                    st.session_state['tasks_df'] = pd.concat([st.session_state['tasks_df'], new_row], ignore_index=True)
                    save_tasks(st.session_state['tasks_df']) # 即保存
                    st.rerun()

    # リスト表示
    df_tasks = st.session_state['tasks_df']
    idx_to_remove = []

    for i, row in df_tasks.iterrows():
        c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
        
        # チェックボックス
        is_done = c1.checkbox("", value=row["done"], key=f"t_{i}")
        
        # 状態が変わったら保存
        if is_done != row["done"]:
            df_tasks.at[i, "done"] = is_done
            save_tasks(df_tasks)
            st.rerun()
            
        # 表示
        if is_done:
            c2.markdown(f"~~{row['task']}~~")
        else:
            c2.markdown(f"**{row['task']}**")
            
        # 削除ボタン
        if c3.button("🗑️", key=f"del_t_{i}"):
            idx_to_remove.append(i)

    # 削除実行
    if idx_to_remove:
        st.session_state['tasks_df'] = df_tasks.drop(idx_to_remove).reset_index(drop=True)
        save_tasks(st.session_state['tasks_df'])
        st.rerun()

# ==========================================
# Tab 2: こころ管理 (編集・自動保存)
# ==========================================
with tab2:
    st.subheader("❤️ 収集リスト")
    st.info("表をタップして直接編集できます。")

    # データエディタ
    edited_df = st.data_editor(
        st.session_state['kokoro_df'],
        num_rows="dynamic",
        column_config={
            "名前": st.column_config.TextColumn("名前", required=True),
            "優先度": st.column_config.SelectboxColumn("優先", options=["高", "中", "低"], width="small"),
            "目標数": st.column_config.NumberColumn("目標", min_value=1, step=1, width="small"),
            "所持数": st.column_config.NumberColumn("所持", min_value=0, step=1, width="small"),
            "完了": st.column_config.CheckboxColumn("済", disabled=True),
        },
        use_container_width=True,
        key="kokoro_editor"
    )

    # 変更があったら保存
    if not edited_df.equals(st.session_state['kokoro_df']):
        # 完了判定ロジック
        edited_df["完了"] = edited_df["所持数"] >= edited_df["目標数"]
        
        # 保存
        st.session_state['kokoro_df'] = edited_df
        save_kokoro(edited_df)
        st.rerun()

    # --- 履歴表示 ---
    st.write("---")
    st.markdown("### 🏆 獲得済み (履歴)")
    completed = edited_df[edited_df["完了"] == True]
    if not completed.empty:
        st.dataframe(completed, use_container_width=True)
    else:
        st.caption("まだ獲得済みのこころはありません。")

# ==========================================
# Tab 3: 外部連携・バックアップ
# ==========================================
with tab3:
    st.subheader("📡 情報収集")
    c1, c2 = st.columns(2)
    c1.link_button("📺 YouTube検索", "https://www.youtube.com/results?search_query=ドラクエウォーク+こころ+最強")
    c2.link_button("🛡️ GameWith", "https://walk.gamewith.jp/")
    
    st.write("---")
    st.subheader("💾 データのバックアップ")
    st.caption("念のため、定期的にデータをダウンロードして保存しておきましょう。")
    
    csv_tasks = st.session_state['tasks_df'].to_csv(index=False).encode('utf-8')
    st.download_button("日課リストを保存", csv_tasks, "tasks.csv", "text/csv")
    
    csv_kokoro = st.session_state['kokoro_df'].to_csv(index=False).encode('utf-8')
    st.download_button("こころリストを保存", csv_kokoro, "kokoro.csv", "text/csv")

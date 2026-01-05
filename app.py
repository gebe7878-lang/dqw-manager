import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta
import altair as alt # グラフ用

# --- 設定: スマホで見やすく (Layout & CSS) ---
st.set_page_config(page_title="DQW Manager V5", page_icon="🛡️", layout="wide")

# スマホ用カスタムCSS (文字を大きく、ボタンを押しやすく)
st.markdown("""
    <style>
    /* 全体の文字サイズアップ */
    html, body, [class*="css"] { font-size: 16px !important; }
    /* チェックボックスの余白拡大 */
    .stCheckbox { padding-top: 10px; padding-bottom: 10px; }
    /* タブの文字を大きく */
    button[data-baseweb="tab"] { font-size: 18px !important; font-weight: bold !important; }
    /* ボタンを指で押しやすく */
    .stButton button { min-height: 50px !important; border-radius: 12px !important; }
    </style>
""", unsafe_allow_html=True)

# 定数
SHEET_NAME = "dqw_data"

# --- 関数: スプレッドシート接続 ---
@st.cache_resource
def init_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# --- 関数: データ読み書き ---
def get_worksheet(worksheet_name, headers=None):
    """シートを取得。なければ作る"""
    client = init_connection()
    sheet = client.open(SHEET_NAME)
    try:
        ws = sheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=worksheet_name, rows=100, cols=20)
        if headers:
            ws.append_row(headers)
    return ws

def load_data(worksheet_name, default_df):
    try:
        ws = get_worksheet(worksheet_name, default_df.columns.tolist())
        data = ws.get_all_records()
        if not data: return default_df
        return pd.DataFrame(data)
    except Exception:
        return default_df

def save_data(worksheet_name, df):
    ws = get_worksheet(worksheet_name)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())

# --- 関数: 履歴ログ記録 ---
def log_history(task_name, is_done):
    """タスクの状態が変わったときに履歴シートに記録する"""
    ws = get_worksheet("history", ["date", "task", "status"])
    today_str = date.today().isoformat()
    
    # 今日のそのタスクのログがあるか確認して更新、なければ追加
    # (簡易実装: 追記型でいくと重くなるので、スプレッドシート側で処理したいが
    #  今回はStreamlit上で処理して書き戻す方式にします)
    try:
        # 全データ取得
        records = ws.get_all_records()
        df_hist = pd.DataFrame(records)
        
        # 既存レコード検索
        mask = (df_hist["date"] == today_str) & (df_hist["task"] == task_name)
        
        if mask.any():
            # 更新
            df_hist.loc[mask, "status"] = "Done" if is_done else "Todo"
        else:
            # 新規
            new_row = {"date": today_str, "task": task_name, "status": "Done" if is_done else "Todo"}
            df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
            
        # 保存 (全書き換えは遅いので、件数が増えたら要注意だが個人利用ならOK)
        ws.clear()
        ws.update([df_hist.columns.values.tolist()] + df_hist.values.tolist())
        
    except Exception as e:
        st.error(f"履歴保存エラー: {e}")

# --- アプリ本体 ---
st.title("🛡️ DQW V5")

# データ初期化
default_tasks = pd.DataFrame([{"task": "デイリークエスト", "done": False}, {"task": "スラミチメダル", "done": False}, {"task": "CM動画", "done": False}])
default_kokoro = pd.DataFrame([{"名前": "キラーマジンガ", "優先度": "高", "目標数": 2, "所持数": 0, "完了": False}])

if 'tasks_df' not in st.session_state:
    st.session_state['tasks_df'] = load_data("tasks", default_tasks)
if 'kokoro_df' not in st.session_state:
    st.session_state['kokoro_df'] = load_data("kokoro", default_kokoro)

# タブ構成
tab1, tab2, tab3 = st.tabs(["✅ 日課", "📊 履歴", "❤️ こころ"])

# ==========================================
# Tab 1: 日課 (スマホ最適化リスト)
# ==========================================
with tab1:
    st.caption(f"📅 {date.today().strftime('%Y/%m/%d')} のタスク")
    
    # 達成率バー
    df_t = st.session_state['tasks_df']
    done_count = len(df_t[df_t['done']==True])
    total_count = len(df_t)
    if total_count > 0:
        progress = done_count / total_count
        st.progress(progress)
        st.caption(f"達成: {done_count}/{total_count}")
    
    st.write("---")
    
    # リスト表示 (表ではなく、大きなチェックボックスを並べる)
    idx_to_remove = []
    
    for i, row in df_t.iterrows():
        # カラム比率: チェックボックス(広め) + 削除ボタン(狭め)
        c1, c2 = st.columns([0.85, 0.15])
        
        # 大きなチェックボックス
        is_checked = c1.checkbox(row['task'], value=row['done'], key=f"check_{i}")
        
        # 状態変化検知 & 履歴ログ保存
        if is_checked != row['done']:
            df_t.at[i, 'done'] = is_checked
            st.session_state['tasks_df'] = df_t
            save_data("tasks", df_t) # マスタ更新
            log_history(row['task'], is_checked) # 履歴記録
            st.rerun()
            
        # 削除ボタン
        if c2.button("🗑️", key=f"del_{i}"):
            idx_to_remove.append(i)

    # 削除実行
    if idx_to_remove:
        st.session_state['tasks_df'] = df_t.drop(idx_to_remove).reset_index(drop=True)
        save_data("tasks", st.session_state['tasks_df'])
        st.rerun()

    # 新規追加エリア
    st.write("---")
    with st.expander("＋ タスクを追加"):
        with st.form("add_task_form", clear_on_submit=True):
            new_task = st.text_input("タスク名")
            if st.form_submit_button("追加", use_container_width=True):
                if new_task:
                    new_row = pd.DataFrame([{"task": new_task, "done": False}])
                    st.session_state['tasks_df'] = pd.concat([st.session_state['tasks_df'], new_row], ignore_index=True)
                    save_data("tasks", st.session_state['tasks_df'])
                    st.rerun()

# ==========================================
# Tab 2: 履歴 (グラフで見える化)
# ==========================================
with tab2:
    st.subheader("📈 過去の活動記録")
    
    if st.button("履歴データを更新"):
        st.cache_data.clear() # キャッシュクリア
        st.rerun()

    try:
        ws_hist = get_worksheet("history", ["date", "task", "status"])
        data_hist = ws_hist.get_all_records()
        
        if data_hist:
            df_hist = pd.DataFrame(data_hist)
            # Doneのものだけ抽出
            df_done = df_hist[df_hist['status'] == 'Done']
            
            if not df_done.empty:
                # 日付ごとの達成数
                daily_counts = df_done.groupby("date").size().reset_index(name="count")
                
                # 棒グラフ (Altair使用)
                chart = alt.Chart(daily_counts).mark_bar().encode(
                    x=alt.X('date', title='日付'),
                    y=alt.Y('count', title='達成数'),
                    tooltip=['date', 'count']
                ).properties(height=300)
                
                st.altair_chart(chart, use_container_width=True)
                
                # 直近の履歴リスト
                st.markdown("##### 直近の達成ログ")
                st.dataframe(df_done.sort_values("date", ascending=False).head(10), use_container_width=True)
            else:
                st.info("まだ達成記録がありません。")
        else:
            st.info("履歴データがまだありません。")
            
    except Exception as e:
        st.error(f"履歴読み込みエラー: {e}")

# ==========================================
# Tab 3: こころ (スマホ最適化)
# ==========================================
with tab3:
    st.caption("こころリスト (タップして編集)")
    
    # データエディタ (ここはExcelライクのままが便利だが、高さを調整)
    edited_df = st.data_editor(
        st.session_state['kokoro_df'],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "名前": st.column_config.TextColumn("名前", required=True),
            "優先度": st.column_config.SelectboxColumn("優先", options=["高", "中", "低"], width="small"),
            "目標数": st.column_config.NumberColumn("目標", width="small"),
            "所持数": st.column_config.NumberColumn("所持", width="small"),
            "完了": st.column_config.CheckboxColumn("済", disabled=True),
        },
        key="kokoro_editor"
    )
    
    if not edited_df.equals(st.session_state['kokoro_df']):
        edited_df["完了"] = edited_df["所持数"] >= edited_df["目標数"]
        st.session_state['kokoro_df'] = edited_df
        save_data("kokoro", edited_df)
        st.rerun()
        
    st.write("---")
    st.link_button("📺 YouTube検索", "https://www.youtube.com/results?search_query=ドラクエウォーク+こころ+最強", use_container_width=True)

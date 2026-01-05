import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime
import altair as alt
import requests
from bs4 import BeautifulSoup

# --- 設定: スマホで見やすく (Layout & CSS) ---
st.set_page_config(page_title="DQW Manager V6", page_icon="🛡️", layout="wide")

# スマホ用カスタムCSS
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 16px !important; }
    .stCheckbox { padding-top: 10px; padding-bottom: 10px; }
    button[data-baseweb="tab"] { font-size: 16px !important; font-weight: bold !important; }
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
    try:
        ws = get_worksheet("history", ["date", "task", "status"])
        today_str = date.today().isoformat()
        records = ws.get_all_records()
        df_hist = pd.DataFrame(records)
        
        mask = (df_hist["date"] == today_str) & (df_hist["task"] == task_name)
        if mask.any():
            df_hist.loc[mask, "status"] = "Done" if is_done else "Todo"
        else:
            new_row = {"date": today_str, "task": task_name, "status": "Done" if is_done else "Todo"}
            df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
            
        ws.clear()
        ws.update([df_hist.columns.values.tolist()] + df_hist.values.tolist())
    except Exception:
        pass

# --- 関数: スクレイピング (Web取込) ---
def fetch_tables_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        response.encoding = response.apparent_encoding
        tables = pd.read_html(response.text)
        return tables
    except Exception as e:
        return []

# --- アプリ本体 ---
st.title("🛡️ DQW V6 (All-in-One)")

# データ初期化
default_tasks = pd.DataFrame([{"task": "デイリークエスト", "done": False}, {"task": "スラミチメダル", "done": False}])
default_kokoro = pd.DataFrame([{"名前": "キラーマジンガ", "優先度": "高", "目標数": 2, "所持数": 0, "完了": False}])

if 'tasks_df' not in st.session_state:
    st.session_state['tasks_df'] = load_data("tasks", default_tasks)
if 'kokoro_df' not in st.session_state:
    st.session_state['kokoro_df'] = load_data("kokoro", default_kokoro)

# タブ構成 (4つになりました)
tab1, tab2, tab3, tab4 = st.tabs(["✅ 日課", "📊 履歴", "❤️ こころ", "🌐 Web取込"])

# ==========================================
# Tab 1: 日課 (スマホ最適化)
# ==========================================
with tab1:
    st.caption(f"📅 {date.today().strftime('%Y/%m/%d')}")
    df_t = st.session_state['tasks_df']
    
    # 達成率
    done_cnt = len(df_t[df_t['done']==True])
    if len(df_t) > 0:
        st.progress(done_cnt / len(df_t))
    
    st.write("---")
    idx_to_remove = []
    for i, row in df_t.iterrows():
        c1, c2 = st.columns([0.85, 0.15])
        is_chk = c1.checkbox(row['task'], value=row['done'], key=f"c_{i}")
        if is_chk != row['done']:
            df_t.at[i, 'done'] = is_chk
            st.session_state['tasks_df'] = df_t
            save_data("tasks", df_t)
            log_history(row['task'], is_chk)
            st.rerun()
        if c2.button("🗑️", key=f"d_{i}"):
            idx_to_remove.append(i)

    if idx_to_remove:
        st.session_state['tasks_df'] = df_t.drop(idx_to_remove).reset_index(drop=True)
        save_data("tasks", st.session_state['tasks_df'])
        st.rerun()

    st.write("---")
    with st.expander("＋ タスク追加"):
        with st.form("add"):
            new = st.text_input("タスク名")
            if st.form_submit_button("追加", use_container_width=True) and new:
                row = pd.DataFrame([{"task": new, "done": False}])
                st.session_state['tasks_df'] = pd.concat([st.session_state['tasks_df'], row], ignore_index=True)
                save_data("tasks", st.session_state['tasks_df'])
                st.rerun()

# ==========================================
# Tab 2: 履歴 (グラフ)
# ==========================================
with tab2:
    if st.button("更新", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    
    try:
        ws = get_worksheet("history", ["date", "task", "status"])
        data = ws.get_all_records()
        if data:
            df_h = pd.DataFrame(data)
            df_d = df_h[df_h['status'] == 'Done']
            if not df_d.empty:
                daily = df_d.groupby("date").size().reset_index(name="count")
                c = alt.Chart(daily).mark_bar().encode(x='date', y='count').properties(height=250)
                st.altair_chart(c, use_container_width=True)
                st.dataframe(df_d.sort_values("date", ascending=False).head(10), use_container_width=True)
            else: st.info("達成なし")
        else: st.info("履歴なし")
    except: st.error("履歴取得エラー")

# ==========================================
# Tab 3: こころ (エディタ)
# ==========================================
with tab3:
    edited = st.data_editor(
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
        key="editor"
    )
    if not edited.equals(st.session_state['kokoro_df']):
        edited["完了"] = edited["所持数"] >= edited["目標数"]
        st.session_state['kokoro_df'] = edited
        save_data("kokoro", edited)
        st.rerun()

# ==========================================
# Tab 4: Web取込 (復活！)
# ==========================================
with tab4:
    st.info("攻略サイトのURLから表を取り込みます")
    url = st.text_input("URL", placeholder="https://walk.gamewith.jp/...")
    
    if st.button("解析", use_container_width=True):
        if url:
            with st.spinner("解析中..."):
                tables = fetch_tables_from_url(url)
            if tables:
                st.success(f"{len(tables)}件の表を発見")
                for i, t in enumerate(tables):
                    with st.expander(f"表 No.{i+1} ({len(t)}件)"):
                        st.dataframe(t)
                        if st.button(f"取込 No.{i+1}", key=f"imp_{i}"):
                            new_items = []
                            try:
                                names = t.iloc[:, 0].astype(str).tolist()
                                current_names = st.session_state['kokoro_df']["名前"].values
                                for n in names:
                                    if n not in current_names:
                                        new_items.append({"名前": n, "優先度": "中", "目標数": 2, "所持数": 0, "完了": False})
                                if new_items:
                                    new_df = pd.DataFrame(new_items)
                                    st.session_state['kokoro_df'] = pd.concat([st.session_state['kokoro_df'], new_df], ignore_index=True)
                                    save_data("kokoro", st.session_state['kokoro_df'])
                                    st.success(f"{len(new_items)}件追加！")
                                    st.rerun()
                                else: st.warning("追加なし")
                            except: st.error("取込失敗")
            else: st.warning("表なし")

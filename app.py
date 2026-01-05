import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup

# --- 設定 ---
st.set_page_config(page_title="DQW Manager Auto", page_icon="🛡️", layout="wide")
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
def load_data(worksheet_name, default_data):
    try:
        client = init_connection()
        sheet = client.open(SHEET_NAME)
        try:
            worksheet = sheet.worksheet(worksheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=20)
            worksheet.update([default_data.columns.values.tolist()] + default_data.values.tolist())
            return default_data
    except Exception as e:
        return default_data

def save_data(worksheet_name, df):
    client = init_connection()
    sheet = client.open(SHEET_NAME)
    worksheet = sheet.worksheet(worksheet_name)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- 関数: スクレイピング (GameWithなどの表を取得) ---
def fetch_tables_from_url(url):
    try:
        # User-Agentを偽装してブラウザからのアクセスに見せる
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.encoding = response.apparent_encoding # 文字化け防止
        
        # PandasでHTML内の<table>をすべて抽出
        tables = pd.read_html(response.text)
        return tables
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return []

# --- アプリ本体 ---
st.title("🛡️ DQW マネージャー (Web取込機能付)")

# 初期データ
default_tasks = pd.DataFrame([{"task": "デイリークエスト", "done": False}])
default_kokoro = pd.DataFrame([{"名前": "キラーマジンガ", "優先度": "高", "目標数": 2, "所持数": 0, "完了": False}])

if 'tasks_df' not in st.session_state:
    st.session_state['tasks_df'] = load_data("tasks", default_tasks)
if 'kokoro_df' not in st.session_state:
    st.session_state['kokoro_df'] = load_data("kokoro", default_kokoro)

tab1, tab2, tab3 = st.tabs(["✅ 日課", "❤️ こころ管理", "🌐 Web取込(New!)"])

# --- Tab 1: 日課 (省略せず前回同様の機能を維持) ---
with tab1:
    st.subheader("今日のタスク")
    # (ここの中身は前回のコードと同じ記述でOKですが、長くなるので省略します。必要なら補完します)
    # 簡易実装:
    df_t = st.session_state['tasks_df']
    edited_t = st.data_editor(df_t, num_rows="dynamic", key="editor_t", use_container_width=True)
    if not edited_t.equals(df_t):
        st.session_state['tasks_df'] = edited_t
        save_data("tasks", edited_t)
        st.rerun()

# --- Tab 2: こころ管理 ---
with tab2:
    st.subheader("こころリスト")
    edited_k = st.data_editor(
        st.session_state['kokoro_df'],
        num_rows="dynamic",
        key="editor_k",
        use_container_width=True,
        column_config={
            "優先度": st.column_config.SelectboxColumn("優先", options=["高", "中", "低"]),
        }
    )
    if not edited_k.equals(st.session_state['kokoro_df']):
        st.session_state['kokoro_df'] = edited_k
        save_data("kokoro", edited_k)
        st.rerun()

# --- Tab 3: スクレイピング機能 (ここがメイン) ---
with tab3:
    st.subheader("🌐 攻略サイトからリストを取り込む")
    st.info("GameWithなどの「最強こころランキング」や「イベントこころリスト」のURLを貼り付けてください。")

    target_url = st.text_input("記事のURL", placeholder="https://walk.gamewith.jp/article/show/...")
    
    if st.button("ページを解析する"):
        if target_url:
            with st.spinner("サイトを解析中..."):
                tables = fetch_tables_from_url(target_url)
                
            if tables:
                st.success(f"{len(tables)} 個の表が見つかりました！")
                
                # 見つかった表を一つずつプレビュー表示
                for i, table in enumerate(tables):
                    with st.expander(f"表 No.{i+1} (データ数: {len(table)})"):
                        st.dataframe(table)
                        
                        # この表を取り込むボタン
                        if st.button(f"この表をリストに追加 (No.{i+1})", key=f"add_tbl_{i}"):
                            # データの整形と追加ロジック
                            # ※表の列名はサイトによって違うので、1列目を「名前」と仮定して取り込む
                            new_items = []
                            try:
                                # 1列目のデータを取得（多くのサイトで1列目がモンスター名）
                                monster_names = table.iloc[:, 0].astype(str).tolist()
                                
                                for name in monster_names:
                                    # 重複チェック
                                    if name not in st.session_state['kokoro_df']["名前"].values:
                                        new_items.append({
                                            "名前": name,
                                            "優先度": "中", # 自動取込は「中」にする
                                            "目標数": 2,     # デフォルト2個
                                            "所持数": 0,
                                            "完了": False
                                        })
                                
                                if new_items:
                                    new_df = pd.DataFrame(new_items)
                                    st.session_state['kokoro_df'] = pd.concat([st.session_state['kokoro_df'], new_df], ignore_index=True)
                                    save_data("kokoro", st.session_state['kokoro_df'])
                                    st.toast(f"{len(new_items)} 件を追加しました！")
                                    st.rerun()
                                else:
                                    st.warning("追加できるデータがありませんでした（すべて登録済みか、空です）。")
                                    
                            except Exception as e:
                                st.error(f"取り込みに失敗しました: {e}")
            else:
                st.warning("表データが見つかりませんでした。別のページを試してください。")

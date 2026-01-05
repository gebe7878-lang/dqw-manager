import streamlit as st
import pandas as pd
from datetime import date, datetime

# --- 設定: 画面の広さを確保 ---
st.set_page_config(page_title="DQW Manager V3", page_icon="🛡️", layout="wide")

# ==========================================
# 関数: データ初期化
# ==========================================
def init_session_state():
    # 日課リストの初期値
    if 'daily_tasks' not in st.session_state:
        st.session_state['daily_tasks'] = [
            {"task": "デイリークエスト", "done": False},
            {"task": "スラミチメダル回収", "done": False},
            {"task": "CM動画視聴", "done": False},
        ]
    
    # こころリストの初期値 (構造を強化: 優先度, 目標数, 所持数)
    if 'kokoro_df' not in st.session_state:
        data = [
            {"名前": "キラーマジンガ", "優先度": "高", "目標数": 2, "所持数": 0, "完了": False},
            {"名前": "覚醒千里行対象", "優先度": "中", "目標数": 4, "所持数": 1, "完了": False},
            {"名前": "メタルキング", "優先度": "低", "目標数": 1, "所持数": 1, "完了": True},
        ]
        st.session_state['kokoro_df'] = pd.DataFrame(data)

init_session_state()

# ==========================================
# メイン画面
# ==========================================
st.title("🛡️ DQW 進捗マネージャー V3")

# タブ構成
tab1, tab2 = st.tabs(["✅ 日課・タスク", "❤️ 欲しい心リスト"])

# ==========================================
# Tab 1: 日課 (追加・削除機能付き)
# ==========================================
with tab1:
    st.subheader("📝 今日の日課")
    st.caption("チェックを入れると完了。項目の追加削除も可能です。")

    # --- 1. タスクリスト表示 ---
    # 削除したいインデックスを保存するリスト
    idx_to_remove = []

    for i, item in enumerate(st.session_state['daily_tasks']):
        col_check, col_name, col_del = st.columns([0.1, 0.7, 0.2])
        
        # チェックボックス
        is_checked = col_check.checkbox("", value=item["done"], key=f"task_{i}")
        st.session_state['daily_tasks'][i]["done"] = is_checked
        
        # タスク名表示（完了なら打消し線）
        if is_checked:
            col_name.markdown(f"~~{item['task']}~~")
        else:
            col_name.markdown(f"**{item['task']}**")
            
        # 削除ボタン
        if col_del.button("🗑️", key=f"del_{i}"):
            idx_to_remove.append(i)

    # 削除処理
    if idx_to_remove:
        for i in sorted(idx_to_remove, reverse=True):
            st.session_state['daily_tasks'].pop(i)
        st.rerun()

    # --- 2. 新規タスク追加 ---
    st.markdown("---")
    with st.expander("＋ 新しい日課を登録する"):
        with st.form("new_task_form", clear_on_submit=True):
            new_task_name = st.text_input("タスク名 (例: ほこら消化)")
            submitted = st.form_submit_button("追加")
            if submitted and new_task_name:
                st.session_state['daily_tasks'].append({"task": new_task_name, "done": False})
                st.rerun()

# ==========================================
# Tab 2: 欲しい心リスト (高機能版)
# ==========================================
with tab2:
    st.subheader("❤️ こころ収集管理")
    st.info("下の表を直接タップして編集できます。「目標数」に達すると自動で「獲得済み」に移動します。")

    # DataFrameを取得
    df = st.session_state['kokoro_df']

    # --- 編集用テーブルの設定 ---
    # 編集されたデータを受け取る
    edited_df = st.data_editor(
        df,
        num_rows="dynamic", # 行の追加削除を許可
        column_config={
            "名前": st.column_config.TextColumn("こころの名前", required=True),
            "優先度": st.column_config.SelectboxColumn(
                "優先度",
                options=["高", "中", "低"],
                required=True,
                width="small"
            ),
            "目標数": st.column_config.NumberColumn("目標", min_value=1, step=1, width="small"),
            "所持数": st.column_config.NumberColumn("所持", min_value=0, step=1, width="small"),
            "完了": st.column_config.CheckboxColumn("完了", disabled=True) # 自動判定のため入力不可に
        },
        use_container_width=True,
        hide_index=True,
        key="editor"
    )

    # --- データの更新と自動判定ロジック ---
    # 所持数 >= 目標数 なら「完了」フラグを立てる
    if not edited_df.equals(df):
        edited_df["完了"] = edited_df["所持数"] >= edited_df["目標数"]
        st.session_state['kokoro_df'] = edited_df
        st.rerun()

    # --- 獲得済みリスト（履歴） ---
    st.markdown("### 🏆 獲得済みコレクション")
    
    # 完了フラグが立っているものだけ抽出
    completed_df = edited_df[edited_df["完了"] == True]
    
    if not completed_df.empty:
        st.dataframe(
            completed_df[["名前", "目標数", "所持数"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("まだコンプリートしたこころはありません。")

    # --- 外部リンク ---
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("📺 YouTubeで最強心を検索", "https://www.youtube.com/results?search_query=ドラクエウォーク+こころ+最強")
    with col2:
        st.link_button("🛡️ 攻略サイト(GameWith)", "https://walk.gamewith.jp/")

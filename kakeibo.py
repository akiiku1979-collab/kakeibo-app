import streamlit as st
import pandas as pd
from datetime import date

# --- 初期設定・データ構造 ---
CATEGORIES = ["食費", "たばこ", "ゲーム", "競馬"]
WEEKS = ["第1週", "第2週", "第3週", "第4週", "第5週"]

# ログイン状態の初期化
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""

# 月ごとのデータを保存するデータベース（辞書）
if "db" not in st.session_state:
    st.session_state.db = {}

# --- アカウント情報（簡易認証用） ---
USERS = {
    "admin": {"pass": "admin", "role": "admin"},
    "husband": {"pass": "husband", "role": "edit"},
    "wife": {"pass": "wife", "role": "edit"},
    "guest": {"pass": "guest", "role": "view"}
}

# --- ログイン画面 ---
if not st.session_state.logged_in:
    st.title("🔐 ログイン")
    st.write("IDとパスワードを入力してください。")
    user_id = st.text_input("ユーザーID")
    password = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        if user_id in USERS and USERS[user_id]["pass"] == password:
            st.session_state.logged_in = True
            st.session_state.role = USERS[user_id]["role"]
            st.session_state.username = user_id
            st.rerun()
        else:
            st.error("IDまたはパスワードが間違っています。")
    st.stop()

# --- サイドバー (ログイン情報) ---
with st.sidebar:
    st.write(f"👤 ログイン中: **{st.session_state.username}**")
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()

# --- メイン画面 ---
st.title("💰 家計管理アプリ")

# 📅 年月の選択 UI（プルダウン）
today = date.today()
col1, col2, _ = st.columns([1, 1, 3])
with col1:
    selected_year = st.selectbox("年", range(today.year - 2, today.year + 3), index=2)
with col2:
    selected_month = st.selectbox("月", range(1, 13), index=today.month - 1)

ym_key = f"{selected_year}年{selected_month}月"

# 選択された年月のデータが存在しない場合は初期化
if ym_key not in st.session_state.db:
    st.session_state.db[ym_key] = {
        "budgets": {cat: 0 for cat in CATEGORIES},
        "actuals": {week: {cat: 0 for cat in CATEGORIES} for week in WEEKS}
    }

current_data = st.session_state.db[ym_key]

# タブの作成
tab1, tab2 = st.tabs(["🗓️ 月別 予算・実績管理", "📊 年間予実・CSV出力"])

with tab1:
    st.subheader(f"【{ym_key}】の予算・実績")
    
    # --- 予算の修正エリア ---
    with st.expander("⚙️ 予算の設定・修正", expanded=False):
        if st.session_state.role in ["admin", "edit"]:
            st.write(f"**{ym_key}** の各費目の予算を入力・変更してください。")
            cols = st.columns(len(CATEGORIES))
            for i, cat in enumerate(CATEGORIES):
                with cols[i]:
                    current_data["budgets"][cat] = st.number_input(
                        f"{cat}の予算", 
                        value=current_data["budgets"][cat], 
                        step=1000,
                        key=f"budget_{ym_key}_{cat}"
                    )
        else:
            st.info("※ guestアカウント（閲覧用）のため予算の変更はできません。")
            for cat in CATEGORIES:
                st.write(f"- {cat}の予算: {current_data['budgets'][cat]:,}円")

    st.markdown("---")
    st.subheader("🗓️ 週別 実績入力")

    # --- 実績の入力エリア ---
    for week in WEEKS:
        with st.expander(week, expanded=(week == "第1週")):
            for cat in CATEGORIES:
                # 残額の計算（予算 - これまでの全週の実績合計）
                total_actual = sum(current_data["actuals"][w][cat] for w in WEEKS)
                remain = current_data["budgets"][cat] - total_actual
                
                st.write(f"**{cat}** (設定予算: {current_data['budgets'][cat]:,}円 / 現在の残額: **{remain:,}円**)")
                
                if st.session_state.role in ["admin", "edit"]:
                    current_data["actuals"][week][cat] = st.number_input(
                        f"{week}の{cat}の実績", 
                        value=current_data["actuals"][week][cat], 
                        step=100, 
                        key=f"actual_{ym_key}_{week}_{cat}",
                        label_visibility="collapsed"
                    )
                else:
                    st.write(f"{week}の実績: {current_data['actuals'][week][cat]:,}円")
            st.write("") 

with tab2:
    st.subheader(f"📊 {selected_year}年の年間予実サマリー")
    
    # 選択された年のデータを集計
    annual_budgets = {cat: 0 for cat in CATEGORIES}
    annual_actuals = {cat: 0 for cat in CATEGORIES}
    
    for key, data in st.session_state.db.items():
        if key.startswith(f"{selected_year}年"):
            for cat in CATEGORIES:
                annual_budgets[cat] += data["budgets"][cat]
                annual_actuals[cat] += sum(data["actuals"][w][cat] for w in WEEKS)

    # サマリーテーブルの表示
    summary_data = []
    for cat in CATEGORIES:
        budget = annual_budgets[cat]
        actual = annual_actuals[cat]
        remain = budget - actual
        summary_data.append({
            "費目": cat,
            "年間予算 (円)": budget,
            "年間実績 (円)": actual,
            "残額 (円)": remain
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    # --- CSV出力データの作成 ---
    st.markdown("---")
    st.write(f"**{selected_year}年** に入力されたすべての月別データをCSVでダウンロードします。")
    
    csv_data = []
    for month in range(1, 13):
        m_key = f"{selected_year}年{month}月"
        if m_key in st.session_state.db:
            m_data = st.session_state.db[m_key]
            for cat in CATEGORIES:
                budget = m_data["budgets"][cat]
                actual = sum(m_data["actuals"][w][cat] for w in WEEKS)
                remain = budget - actual
                csv_data.append({
                    "年月": m_key,
                    "費目": cat,
                    "予算": budget,
                    "実績": actual,
                    "残額": remain
                })
    
    if csv_data:
        df_csv = pd.DataFrame(csv_data)
        csv_export = df_csv.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="📥 CSVをダウンロード",
            data=csv_export,
            file_name=f"kakeibo_data_{selected_year}.csv",
            mime="text/csv"
        )
    else:
        st.info("データがまだ入力されていません。")

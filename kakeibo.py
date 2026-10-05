import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import calendar

# --- 初期設定・データ構造 ---
CATEGORIES = ["食費", "たばこ", "ゲーム", "競馬"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""

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

# --- サイドバー ---
with st.sidebar:
    st.write(f"👤 ログイン中: **{st.session_state.username}**")
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()

# --- メイン画面 ---
st.title("💰 家計管理アプリ")

# 📅 日本時間(JST)のリアルタイム日付を取得
JST = timezone(timedelta(hours=+9), 'JST')
today = datetime.now(JST).date()

# カレンダー形式のUI（買ったその場の入力用に「今日」が初期値。過去も選択可能）
selected_date = st.date_input("🗓 買い物をした日付を選択してください", value=today)

# 選択された日付から年・月・日を抽出
selected_year = selected_date.year
selected_month = selected_date.month
selected_day = selected_date.day

ym_key = f"{selected_year}年{selected_month}月"
_, max_days = calendar.monthrange(selected_year, selected_month)

# データベースの初期化
if ym_key not in st.session_state.db:
    st.session_state.db[ym_key] = {
        "budgets": {cat: 0 for cat in CATEGORIES},
        "actuals": {d: {cat: 0 for cat in CATEGORIES} for d in range(1, 32)}
    }
else:
    # 過去の週別フォーマットが残っていれば日別にリセット
    if "第1週" in st.session_state.db[ym_key]["actuals"]:
        st.session_state.db[ym_key]["actuals"] = {d: {cat: 0 for cat in CATEGORIES} for d in range(1, 32)}

current_data = st.session_state.db[ym_key]

# タブの作成
tab1, tab2 = st.tabs(["🗓️ 日別入力・月別管理", "📊 年間予実・CSV出力"])

with tab1:
    # --- 予算設定エリア ---
    with st.expander("⚙ 予算の設定・修正", expanded=False):
        if st.session_state.role in ["admin", "edit"]:
            st.write(f"**{ym_key}** の予算を入力してください。")
            b_cols = st.columns(len(CATEGORIES))
            for i, cat in enumerate(CATEGORIES):
                with b_cols[i]:
                    current_data["budgets"][cat] = st.number_input(
                        f"{cat}の予算", 
                        value=current_data["budgets"][cat], 
                        step=1000,
                        key=f"budget_{ym_key}_{cat}"
                    )
        else:
            st.info("※ guestアカウントのため予算変更はできません。")
            for cat in CATEGORIES:
                st.write(f"- {cat}の予算: {current_data['budgets'][cat]:,}円")

    st.markdown("---")
    
    # --- 日別入力エリア ---
    st.subheader(f"✏ {selected_month}月{selected_day}日 の実績入力")
    
    input_cols = st.columns(2)
    for i, cat in enumerate(CATEGORIES):
        col = input_cols[i % 2]
        with col:
            # その月の合計実績と残額を計算
            total_actual = sum(current_data["actuals"][d].get(cat, 0) for d in range(1, max_days + 1))
            remain = current_data["budgets"][cat] - total_actual
            
            st.write(f"**{cat}** (今月の残額: {remain:,}円)")
            
            if st.session_state.role in ["admin", "edit"]:
                current_data["actuals"][selected_day][cat] = st.number_input(
                    f"{cat}の実績", 
                    value=current_data["actuals"][selected_day].get(cat, 0), 
                    step=100, 
                    key=f"act_{ym_key}_{selected_day}_{cat}",
                    label_visibility="collapsed"
                )
            else:
                st.write(f"{current_data['actuals'][selected_day].get(cat, 0):,}円")

    st.markdown("---")

    # --- 月間データ一覧表 ---
    with st.expander(f"📋 {selected_month}月の日別データを一覧で見る / 編集する"):
        st.write("表の数値を直接クリックして変更することも可能です。")
        
        df_data = []
        for d in range(1, max_days + 1):
            row = {"日": f"{d}日"}
            for cat in CATEGORIES:
                row[cat] = current_data["actuals"][d].get(cat, 0)
            df_data.append(row)
        df_month = pd.DataFrame(df_data).set_index("日")
        
        if st.session_state.role in ["admin", "edit"]:
            edited_df = st.data_editor(df_month, use_container_width=True)
            for d in range(1, max_days + 1):
                day_str = f"{d}日"
                for cat in CATEGORIES:
                    current_data["actuals"][d][cat] = int(edited_df.loc[day_str, cat])
        else:
            st.dataframe(df_month, use_container_width=True)

with tab2:
    st.subheader(f"📊 {selected_year}年の年間予実サマリー")
    
    annual_budgets = {cat: 0 for cat in CATEGORIES}
    annual_actuals = {cat: 0 for cat in CATEGORIES}
    
    for key, data in st.session_state.db.items():
        if key.startswith(f"{selected_year}年"):
            for cat in CATEGORIES:
                annual_budgets[cat] += data["budgets"][cat]
                annual_actuals[cat] += sum(data["actuals"][d].get(cat, 0) for d in range(1, 32))

    summary_data = []
    for cat in CATEGORIES:
        budget = annual_budgets[cat]
        actual = annual_actuals[cat]
        summary_data.append({
            "費目": cat,
            "年間予算": f"{budget:,} 円",
            "年間実績": f"{actual:,} 円",
            "残額": f"{budget - actual:,} 円"
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    # --- CSV出力 ---
    st.markdown("---")
    st.write(f"**{selected_year}年** の月別サマリーをCSVでダウンロードします。")
    
    csv_data = []
    for month in range(1, 13):
        m_key = f"{selected_year}年{month}月"
        if m_key in st.session_state.db:
            m_data = st.session_state.db[m_key]
            for cat in CATEGORIES:
                budget = m_data["budgets"][cat]
                actual = sum(m_data["actuals"][d].get(cat, 0) for d in range(1, 32))
                csv_data.append({
                    "年月": m_key,
                    "費目": cat,
                    "予算": budget,
                    "実績": actual,
                    "残額": budget - actual
                })
    
    if csv_data:
        csv_export = pd.DataFrame(csv_data).to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSVをダウンロード",
            data=csv_export,
            file_name=f"kakeibo_data_{selected_year}.csv",
            mime="text/csv"
        )
    else:
        st.info("データがまだ入力されていません。")

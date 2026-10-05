import streamlit as st
import pandas as pd

# --- 初期設定・データ構造 ---
CATEGORIES = ["食費", "たばこ", "ゲーム", "競馬"]
WEEKS = ["第1週", "第2週", "第3週", "第4週", "第5週"]

# セッション状態の初期化（予算と実績データ）
if "budgets" not in st.session_state:
    st.session_state.budgets = {cat: 0 for cat in CATEGORIES}

if "actuals" not in st.session_state:
    # 費目ごと・週ごとの実績を管理
    st.session_state.actuals = {week: {cat: 0 for cat in CATEGORIES} for week in WEEKS}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""

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
st.title("💰 家計管理アプリ (予算・実績・年間予実)")

# タブの作成
tab1, tab2 = st.tabs(["🗓️ 月別 予算・実績管理", "📊 年間予実・CSV出力"])

with tab1:
    # --- 予算の修正エリア ---
    with st.expander("⚙️ 予算の設定・修正", expanded=False):
        if st.session_state.role in ["admin", "edit"]:
            st.write("各費目の予算を入力・変更してください。")
            cols = st.columns(len(CATEGORIES))
            for i, cat in enumerate(CATEGORIES):
                with cols[i]:
                    st.session_state.budgets[cat] = st.number_input(
                        f"{cat}の予算", 
                        value=st.session_state.budgets[cat], 
                        step=1000,
                        key=f"budget_{cat}"
                    )
        else:
            st.info("※ guestアカウント（閲覧用）のため予算の変更はできません。")
            for cat in CATEGORIES:
                st.write(f"- {cat}の予算: {st.session_state.budgets[cat]:,}円")

    st.markdown("---")
    st.subheader("🗓️ 週別 予算・実績入力")

    # --- 実績の入力エリア ---
    for week in WEEKS:
        with st.expander(week, expanded=(week == "第1週")):
            for cat in CATEGORIES:
                # 残額の計算（予算 - これまでの全週の実績合計）
                total_actual = sum(st.session_state.actuals[w][cat] for w in WEEKS)
                remain = st.session_state.budgets[cat] - total_actual
                
                st.write(f"**{cat}** (設定予算: {st.session_state.budgets[cat]:,}円 / 現在の残額: **{remain:,}円**)")
                
                if st.session_state.role in ["admin", "edit"]:
                    st.session_state.actuals[week][cat] = st.number_input(
                        f"{week}の{cat}の実績", 
                        value=st.session_state.actuals[week][cat], 
                        step=100, 
                        key=f"actual_{week}_{cat}",
                        label_visibility="collapsed"
                    )
                else:
                    st.write(f"{week}の実績: {st.session_state.actuals[week][cat]:,}円")
            st.write("") # スペース調整

with tab2:
    st.subheader("📊 年間予実サマリー")
    
    # テーブル表示用のデータ作成
    data = []
    for cat in CATEGORIES:
        budget = st.session_state.budgets[cat]
        actual = sum(st.session_state.actuals[w][cat] for w in WEEKS)
        remain = budget - actual
        data.append({
            "費目": cat,
            "予算 (円)": budget,
            "実績合計 (円)": actual,
            "残額 (円)": remain
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

    # --- CSV出力 ---
    st.markdown("---")
    st.write("現在のデータをCSVファイルとしてダウンロードします。")
    # 文字化け防止のため utf-8-sig でエンコード
    csv = df.to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 CSVをダウンロード",
        data=csv,
        file_name="kakeibo_data.csv",
        mime="text/csv"
    )

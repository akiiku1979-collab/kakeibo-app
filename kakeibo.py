import streamlit as st
import pandas as pd
import io

# ページの設定
st.set_page_config(page_title="家計管理アプリ", page_icon="💰", layout="centered")

# --- 認証管理（4アカウント対応） ---
USERS = {
    "admin": {"pass": "admin", "role": "管理者"},
    "husband": {"pass": "husband", "role": "私（編集可）"},
    "wife": {"pass": "wife", "role": "妻（編集可）"},
    "guest": {"pass": "guest", "role": "予備（閲覧のみ）"}
}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.authenticated:
    st.title("🔒 ログイン")
    st.write("アカウント情報を入力してください。")
    username_input = st.text_input("ID")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username_input in USERS and USERS[username_input]["pass"] == password_input:
            st.session_state.authenticated = True
            st.session_state.username = username_input
            st.rerun()
        else:
            st.error("⚠️ IDまたはパスワードが間違っています")
else:
    current_user = st.session_state.username
    user_role = USERS[current_user]["role"]
    
    # --- ログイン成功後のメイン画面 ---
    st.title("💰 家計管理アプリ（予算・実績・年間予実）")
    st.sidebar.info(urgical := f"ログイン中: **{current_user}** ({user_role})")
    
    if st.sidebar.button("ログアウト"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    # タブ切り替え（1画面タブ切り替え設計）
    tab_monthly, tab_yearly = st.tabs(["📅 月別 予算・実績管理", "📊 年間予実・CSV出力"])

    items = ["食費", "たばこ", "ゲーム", "競馬"]

    # セッションステートでのデータ保持（月別データ）
    if "monthly_data" not in st.session_state:
        # サンプルとして7月のデータを初期格納
        init_budget = {"食費_予算": 12000, "たばこ_予算": 2850, "ゲーム_予算": 4000, "競馬_予算": 2000}
        init_actual = {"食費_実績": 0, "たばこ_実績": 0, "ゲーム_実績": 0, "競馬_実績": 0}
        
        weeks_data = []
        for i in range(1, 6):
            row = {"週": f"第{i}週"}
            for item in items:
                row[f"{item}_予算"] = init_budget[f"{item}_予算"] // 5
                row[f"{item}_実績"] = 0
            weeks_data.append(row)
        st.session_state.monthly_data = pd.DataFrame(weeks_data)

    with tab_monthly:
        st.subheader("📅 週別 予算・実績入力")
        
        is_editable = user_role != "予備（閲覧のみ）"
        if not is_editable:
            st.warning("⚠️ 現在「予備（閲覧のみ）」アカウントのため、数値の変更はできません。")

        df_mon = st.session_state.monthly_data
        
        for i in range(len(df_mon)):
            with st.expander(f"📅 {df_mon.loc[i, '週']}", expanded=True if i==0 else False):
                total_budget = 0
                total_actual = 0
                
                for item in items:
                    budget = int(df_mon.loc[i, f"{item}_予算"])
                    total_budget += budget
                    
                    current_actual = int(df_mon.loc[i, f"{item}_実績"])
                    if is_editable:
                        actual = st.number_input(
                            f"{item} (予算: {budget:,}円)", 
                            min_value=0, 
                            value=current_actual,
                            step=100,
                            key=f"{item}_{i}"
                        )
                        df_mon.loc[i, f"{item}_実績"] = actual
                    else:
                        actual = current_actual
                        st.text(f"{item} (予算: {budget:,}円) - 実績: {actual:,}円")
                        
                    total_actual += actual
                    
                diff = total_budget - total_actual
                if diff >= 0:
                    st.success(f"🌟 今週の合計: {total_actual:,}円 / 予算: {total_budget:,}円 （残り: {diff:,}円）")
                else:
                    st.error(f"⚠️ 今週の合計: {total_actual:,}円 / 予算: {total_budget:,}円 （オーバー: {-diff:,}円）")

        st.divider()
        st.subheader("📊 月間サマリー")
        total_b_all = sum(int(df_mon[f"{item}_予算"].sum()) for item in items)
        total_a_all = sum(int(df_mon[f"{item}_実績"].sum()) for item in items)
        total_d_all = total_b_all - total_a_all

        col1, col2, col3 = st.columns(3)
        col1.metric("月間全体の予算", f"{total_b_all:,}円")
        col2.metric("現在の月間実績", f"{total_a_all:,}円")
        col3.metric("月間残額", f"{total_d_all:,}円")

    with tab_yearly:
        st.subheader("📊 年間予実管理 & CSV出力")
        st.write("年間を通じた予実の集計と、CSVファイル形式での出力を行います。")
        
        # 年間サマリー用のダミーフレーム（年間通算のイメージ）
        yearly_summary = []
        for m in range(1, 13):
            m_budget = total_b_all
            m_actual = total_a_all if m == 7 else 0  # 7月以外は実績0とするサンプル
            yearly_summary.append({
                "年月": f"2026年{m:02d}月",
                "予算合計": m_budget,
                "実績合計": m_actual,
                "残額": m_budget - m_actual
            })
        df_yearly = pd.DataFrame(yearly_summary)
        
        st.dataframe(df_yearly, use_container_width=True)
        
        # CSV出力機能
        csv_buffer = io.StringIO()
        df_yearly.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 年間予実データをCSVダウンロード",
            data=csv_data,
            file_name="yearly_budget_summary.csv",
            mime="text/csv"
        )
# ==================== SECTION 1: IMPORT & CSS ====================

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="REASON Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        background: linear-gradient(90deg, #2a5298 0%, #3a6bc2 100%);
        padding: 0.6rem 1rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 1rem;
    }
    .stat-card {
        background-color: #f0f4ff;
        border: 1px solid #c0d0f0;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==================== SECTION 2: LOOKUP TABLE ====================

_USER_STATUS_MAP = {}
for _id in [83118188, 147875, 241140, 240952, 242340, 146829, 171915, 253028, 154327, 240623,
            240951, 240624, 253044, 150292, 241162, 252404, 253048, 240957, 241434, 240168, 240625, 253031]:
    _USER_STATUS_MAP[_id] = 'Crew Training'
    _USER_STATUS_MAP[str(_id)] = 'Crew Training'

for _id in [84116714, 'M14647', 82088093, 82120906, 242333, 253038, 153009, 241794, 241441, 82116818,
            134744, 240432, 150283, 242334, 241169, 84104580, 252404, 151122, 82102045, 242332, 252000,
            84122780, 242335, 240711, 134741, 240431, 242344, 82104894, 242342, 240723, 220260, 253045, 242047, 252403]:
    _USER_STATUS_MAP[_id] = 'Crew Control'
    if isinstance(_id, int):
        _USER_STATUS_MAP[str(_id)] = 'Crew Control'

for _id in [84101641, 220515, 242338, 221027, 251997, 84120306, 142686, 240627, 84103500, 252003,
            240628, 84120287, 143516, 242329, 252004, 240626, 221399, 241797, 240738, 252002, 241201, 260062, 260058]:
    _USER_STATUS_MAP[_id] = 'Tracking'
    _USER_STATUS_MAP[str(_id)] = 'Tracking'

for _id in [84052867, 140108, 82119055, 150296, 151118, 135254, 147426, 142543]:
    _USER_STATUS_MAP[_id] = 'Paxlist'
    _USER_STATUS_MAP[str(_id)] = 'Paxlist'

# ==================== SECTION 3: HELPER FUNCTIONS ====================

def parse_admin_column_vectorized(series: pd.Series) -> pd.DataFrame:
    s = series.astype(str).str.strip()
    extracted = s.str.extract(
        r'^(?P<ADMIN_NAME>[^-]+?)\s*-\s*(?P<ADMIN_ID>[^(]+?)(?:\s*\((?P<ADMIN_USER>[^)]+)\))?\s*$'
    )
    no_match = extracted['ADMIN_NAME'].isna()
    extracted.loc[no_match, 'ADMIN_NAME'] = s[no_match]
    extracted = extracted.where(series.notna(), other=None)
    extracted['ADMIN_ID']   = extracted['ADMIN_ID'].str.strip()
    extracted['ADMIN_NAME'] = extracted['ADMIN_NAME'].str.strip()
    extracted['ADMIN_USER'] = extracted['ADMIN_USER'].str.strip()
    return extracted


def add_reason_status(df: pd.DataFrame) -> pd.DataFrame:
    mask = df['REASON'].notna() & (df['REASON'].astype(str).str.strip() != '')
    df['Reason Status'] = np.where(mask, 'WITH REASON', 'NO REASON')
    return df


def add_std_local_time(df: pd.DataFrame) -> pd.DataFrame:
    df['STD (Local Time)'] = pd.to_datetime(df['STD (UTC Time)'], errors='coerce') + pd.Timedelta(hours=7)
    return df


def add_user_status(df: pd.DataFrame) -> pd.DataFrame:
    admin_id  = df['ADMIN_ID']
    int_keys  = pd.to_numeric(admin_id, errors='coerce')
    status    = int_keys.map(_USER_STATUS_MAP)
    mask_un   = status.isna()
    status[mask_un] = admin_id[mask_un].map(_USER_STATUS_MAP)
    df['User Status'] = status.fillna('OTHER')
    return df


def add_action_time_status(df: pd.DataFrame) -> pd.DataFrame:
    action_date = pd.to_datetime(df['ACTION TIME (CGK Time)'], errors='coerce').dt.normalize()
    std_date    = pd.to_datetime(df['STD (Local Time)'],        errors='coerce').dt.normalize()
    delta       = (std_date - action_date).dt.days
    conditions  = [delta == 0, delta == 1, delta == 2, delta == 3, delta > 3]
    choices     = ['D-DAY', 'D-1', 'D-2', 'D-3', 'Before D-3']
    df['Action Time Status'] = np.select(conditions, choices, default='OTHER')
    return df


def standardize_action_time(df: pd.DataFrame) -> pd.DataFrame:
    col  = df['ACTION TIME (CGK Time)'].astype(str).str.strip()
    fmt1 = pd.to_datetime(col, format='%m/%d/%Y %H:%M', errors='coerce')
    fmt2 = pd.to_datetime(col, format='%d-%b-%y %H:%M', errors='coerce')
    fmt3 = pd.to_datetime(col, errors='coerce', dayfirst=False)
    df['ACTION TIME (CGK Time)'] = fmt1.fillna(fmt2).fillna(fmt3)
    return df


def clean_reason_column_vectorized(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.split(' - ').str[0].str.strip()
    s = s.str.replace(r'^(\d+)\.(\d+)\s+', r'\2 ', regex=True)
    s = s.str.replace(r'^(\d+)\.\s*', '', regex=True)
    s = s.str.strip()
    return s.where(series.notna(), other=np.nan)


def to_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    output.seek(0)
    return output


# ==================== SECTION 4: CORE PROCESSING (CACHED) ====================

@st.cache_data(show_spinner=False)
def clean_and_process(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run full clean + process pipeline.
    Returns (df_cleaned, df_processed).
    Cached — only reruns when input DataFrame changes.
    """
    # --- CLEAN ---
    df = standardize_action_time(df)
    df['REASON'] = clean_reason_column_vectorized(df['REASON'])
    df = df.drop_duplicates(
        subset=['ROSTER DATE', 'ID', 'NAME', 'REASON', 'ACTIVITY BEFORE', 'ACTIVITY AFTER'],
        keep='last'
    )
    df['ROSTER DATE']    = pd.to_datetime(df['ROSTER DATE'],    errors='coerce')
    df['STD (UTC Time)'] = pd.to_datetime(df['STD (UTC Time)'], errors='coerce')
    std_local = df['STD (UTC Time)'] + pd.Timedelta(hours=7)
    df = df[df['ROSTER DATE'].dt.date == std_local.dt.date].copy()
    df_cleaned = df.copy()

    # --- PROCESS ---
    admin_parsed     = parse_admin_column_vectorized(df['ADMIN'])
    df['ADMIN_NAME'] = admin_parsed['ADMIN_NAME'].values
    df['ADMIN_ID']   = admin_parsed['ADMIN_ID'].values
    df['ADMIN_USER'] = admin_parsed['ADMIN_USER'].values
    df = add_reason_status(df)
    df = add_std_local_time(df)
    df = add_user_status(df)
    df = add_action_time_status(df)
    df_processed = df.copy()

    return df_cleaned, df_processed


# ==================== SECTION 5: SESSION STATE INIT ====================

for key in ('df_combined', 'df_cleaned', 'df_processed'):
    if key not in st.session_state:
        st.session_state[key] = None

# ==================== SECTION 6: SIDEBAR NAVIGATION ====================

st.sidebar.markdown("""
<div style="text-align:center; padding: 0.5rem 0 1rem 0;">
    <span style="font-size:1.4rem; font-weight:700; color:#1e3c72;">📊 REASON Analysis</span>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navigasi Menu",
    options=["📂 Menu 1 — Gabung File", "⚙️ Menu 2 — Cleaning & Analisis"],
    index=0
)

st.sidebar.markdown("---")

# ==================== SECTION 7: HEADER ====================

st.markdown("""
<div class="main-header">
    <h1 style="color: white;">📊 REASON Modification Analysis</h1>
    <p>Analyze Crew Roster Modification Log</p>
</div>
""", unsafe_allow_html=True)

# ====================================================================================
# MENU 1 — GABUNG FILE
# ====================================================================================

if menu == "📂 Menu 1 — Gabung File":

    st.markdown('<div class="section-header"><h3 style="margin:0; color:white;">📂 Menu 1 — Gabung File Excel</h3></div>', unsafe_allow_html=True)
    st.write("Gabungkan satu atau lebih file Excel menjadi satu dataset. Hasil gabungan dapat dipreview dan didownload, atau langsung dilanjutkan ke Menu 2.")

    # --- Upload ---
    with st.sidebar:
        st.header("📁 Upload File")
        num_files = st.number_input("Jumlah file:", min_value=1, max_value=10, value=1)
        uploaded_files = []
        for i in range(num_files):
            f = st.file_uploader(f"File {i+1}:", type="xlsx", key=f"m1_file_{i}")
            if f:
                uploaded_files.append(f)
        gabung_button = st.button("🔗 Gabungkan File", use_container_width=True)

    # --- Process ---
    if gabung_button:
        if not uploaded_files:
            st.warning("⚠️ Belum ada file yang diupload.")
        else:
            with st.spinner("⏳ Menggabungkan file..."):
                try:
                    dfs = [pd.read_excel(f) for f in uploaded_files]
                    combined = pd.concat(dfs, ignore_index=True)
                    st.session_state.df_combined = combined
                    # Reset downstream hasil agar Menu 2 tahu data berubah
                    st.session_state.df_cleaned   = None
                    st.session_state.df_processed = None
                    st.success(f"✅ {len(uploaded_files)} file berhasil digabungkan!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    # --- Tampilkan hasil jika sudah ada ---
    if st.session_state.df_combined is not None:
        df_combined = st.session_state.df_combined

        st.markdown("---")

        # Statistik ringkas
        st.subheader("📊 Statistik Hasil Gabungan")
        dupes = df_combined.duplicated(
            subset=['ROSTER DATE', 'ID', 'NAME', 'REASON', 'ACTIVITY BEFORE', 'ACTIVITY AFTER']
        ).sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Baris",    f"{len(df_combined):,}")
        c2.metric("Total Kolom",    len(df_combined.columns))
        c3.metric("Potensi Duplikat", f"{dupes:,}")
        c4.metric("File Digabung",  len(uploaded_files) if uploaded_files else "—")

        st.markdown("---")

        # Preview tabel
        st.subheader("👁️ Preview Data Gabungan")
        st.caption(f"Menampilkan 100 baris pertama dari {len(df_combined):,} baris total.")
        st.dataframe(df_combined.head(100), use_container_width=True, height=400)

        st.markdown("---")

        # Download
        st.subheader("📥 Download Hasil Gabungan")
        col_dl, col_info = st.columns([1, 2])
        with col_dl:
            st.download_button(
                label="⬇️ Download Gabungan (.xlsx)",
                data=to_excel(df_combined),
                file_name=f"REASON_Gabungan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_info:
            st.info("💡 Data ini sudah tersimpan di sesi. Pindah ke **Menu 2** untuk melanjutkan proses cleaning & analisis tanpa perlu upload ulang.")

    else:
        st.info("👈 Upload file Excel di sidebar, lalu klik **Gabungkan File**.")


# ====================================================================================
# MENU 2 — CLEANING & ANALISIS
# ====================================================================================

elif menu == "⚙️ Menu 2 — Cleaning & Analisis":

    st.markdown('<div class="section-header"><h3 style="margin:0; color:white;">⚙️ Menu 2 — Cleaning & Analisis</h3></div>', unsafe_allow_html=True)

    # --- Sumber data: dari Menu 1 atau upload baru ---
    with st.sidebar:
        st.header("📁 Sumber Data")

        if st.session_state.df_combined is not None:
            sumber = st.radio(
                "Gunakan data dari:",
                options=["✅ Hasil Menu 1 (sudah digabung)", "📤 Upload file baru"],
                index=0,
                key="m2_sumber"
            )
        else:
            sumber = "📤 Upload file baru"
            st.info("Belum ada data dari Menu 1. Silakan upload file di bawah.")

        # Upload baru jika dipilih
        m2_uploaded = None
        if sumber == "📤 Upload file baru":
            num_files_m2 = st.number_input("Jumlah file:", min_value=1, max_value=10, value=1, key="m2_num")
            m2_files = []
            for i in range(num_files_m2):
                f = st.file_uploader(f"File {i+1}:", type="xlsx", key=f"m2_file_{i}")
                if f:
                    m2_files.append(f)
            if m2_files:
                m2_uploaded = m2_files

        proses_button = st.button("🔄 Proses Data", use_container_width=True)

    # --- Tentukan DataFrame input ---
    if proses_button:
        with st.spinner("⏳ Memproses data..."):
            try:
                # Ambil sumber data
                if sumber == "✅ Hasil Menu 1 (sudah digabung)":
                    df_input = st.session_state.df_combined.copy()
                    st.info(f"📊 Menggunakan data dari Menu 1 ({len(df_input):,} baris).")
                else:
                    if not m2_uploaded:
                        st.warning("⚠️ Belum ada file yang diupload.")
                        st.stop()
                    dfs = [pd.read_excel(f) for f in m2_uploaded]
                    df_input = pd.concat(dfs, ignore_index=True)
                    st.info(f"📊 Menggabungkan {len(m2_uploaded)} file ({len(df_input):,} baris).")

                # Jalankan pipeline (cached)
                df_cleaned, df_processed = clean_and_process(df_input)
                st.session_state.df_cleaned   = df_cleaned
                st.session_state.df_processed = df_processed

                # Ringkasan proses
                removed = len(df_input) - len(df_cleaned)
                c1, c2, c3 = st.columns(3)
                c1.metric("Data Masuk",      f"{len(df_input):,}")
                c2.metric("Setelah Cleaning", f"{len(df_cleaned):,}")
                c3.metric("Baris Dihapus",    f"{removed:,}")
                st.success("✅ Data berhasil diproses!")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    # --- Tampilkan analisis jika sudah ada hasil ---
    if st.session_state.df_processed is not None:
        df_processed = st.session_state.df_processed

        st.markdown("---")

        # --- Filter ---
        st.sidebar.markdown("---")
        st.sidebar.header("🔍 Filter Data")

        companies          = df_processed['COMPANY'].unique()
        ats_list           = df_processed['Action Time Status'].unique()
        us_list            = df_processed['User Status'].unique()
        rs_list            = df_processed['Reason Status'].unique()

        sel_companies = st.sidebar.multiselect("COMPANY:",            companies, default=companies)
        sel_ats       = st.sidebar.multiselect("Action Time Status:", ats_list,  default=ats_list)
        sel_us        = st.sidebar.multiselect("User Status:",        us_list,   default=us_list)
        sel_rs        = st.sidebar.multiselect("Reason Status:",      rs_list,   default=rs_list)

        mask = (
            df_processed['COMPANY'].isin(sel_companies) &
            df_processed['Action Time Status'].isin(sel_ats) &
            df_processed['User Status'].isin(sel_us) &
            df_processed['Reason Status'].isin(sel_rs)
        )
        df_filtered = df_processed[mask]

        # --- Metrics ---
        rs  = df_filtered['Reason Status']
        ats = df_filtered['Action Time Status']
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total Records", f"{len(df_filtered):,}")
        c2.metric("With Reason",   f"{(rs  == 'WITH REASON').sum():,}")
        c3.metric("No Reason",     f"{(rs  == 'NO REASON').sum():,}")
        c4.metric("D-DAY",         f"{(ats == 'D-DAY').sum():,}")
        c5.metric("D-1",           f"{(ats == 'D-1').sum():,}")
        c6.metric("D-3",           f"{(ats == 'D-3').sum():,}")

        st.markdown("---")

        # --- Visualisasi ---
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("📊 Distribusi Reason Status")
            rc = df_filtered['Reason Status'].value_counts()
            fig = px.pie(values=rc.values, names=rc.index,
                         title="Reason Status Distribution",
                         color_discrete_sequence=px.colors.sequential.RdBu)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.subheader("📈 Distribusi Action Time Status")
            ac = df_filtered['Action Time Status'].value_counts()
            fig = px.bar(x=ac.index, y=ac.values,
                         title="Action Time Status Distribution",
                         labels={'x': 'Action Time Status', 'y': 'Count'},
                         color=ac.index,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        col_l2, col_r2 = st.columns(2)

        with col_l2:
            st.subheader("🔤 Top 5 REASON")
            rb = df_filtered['REASON'].value_counts().head(5).sort_values(ascending=True)
            rp = (rb / rb.sum() * 100).round(2)
            fig = px.bar(x=rp.values, y=rp.index, orientation='h',
                         title="Top 5 REASON (%)",
                         labels={'x': 'Percentage (%)', 'y': 'REASON'},
                         text=rp.values)
            fig.update_traces(textposition='outside', texttemplate='%{text:.2f}%')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with col_r2:
            st.subheader("👥 User Status Distribution")
            uc = df_filtered['User Status'].value_counts()
            fig = px.bar(x=uc.index, y=uc.values,
                         title="User Status Distribution",
                         labels={'x': 'User Status', 'y': 'Count'},
                         color=uc.index,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- Detail Data ---
        st.subheader("📑 Detail Data")
        display_cols = ['ID', 'NAME', 'COMPANY', 'ROSTER DATE', 'ACTIVITY', 'REASON',
                        'STD (Local Time)', 'ACTION TIME (CGK Time)', 'User Status',
                        'Action Time Status', 'ADMIN']
        avail_cols = [c for c in display_cols if c in df_filtered.columns]
        st.dataframe(df_filtered[avail_cols], use_container_width=True, height=400)

        st.markdown("---")

        # --- Download ---
        st.subheader("📥 Download Data")
        cd1, cd2 = st.columns(2)
        with cd1:
            st.download_button(
                label="⬇️ Download Data Cleaned",
                data=to_excel(st.session_state.df_cleaned),
                file_name=f"REASON_Cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with cd2:
            st.download_button(
                label="⬇️ Download Data Hasil Analisis",
                data=to_excel(df_filtered),
                file_name=f"REASON_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    else:
        st.info("👈 Pilih sumber data di sidebar, lalu klik **Proses Data** untuk memulai analisis.")

# ==================== FOOTER ====================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Crew Roster Modification Log Analysis Tool</p>
    <p><small>© Maurino Audrian Putra</small></p>
</div>
""", unsafe_allow_html=True)

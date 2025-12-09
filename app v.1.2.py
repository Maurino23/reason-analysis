import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(page_title="REASON Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")

# CSS untuk styling
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
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #cce7ff;
        border: 1px solid #99d5ff;
        color: #004080;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FUNCTIONS ====================

def parse_admin_column(admin_str):
    """Split ADMIN column into ADMIN, ADMIN_ID, and USER"""
    if pd.isna(admin_str):
        return None, None, None
    
    try:
        # Format: "ADMIN - ID (USER)"
        admin_str = str(admin_str).strip()
        
        # Split by ' - ' (space-dash-space)
        parts = admin_str.split(' - ')
        if len(parts) < 2:
            return admin_str, None, None
        
        admin = parts[0].strip()
        rest = parts[1].strip()
        
        # Extract ID and USER from "ID (USER)" format
        if '(' in rest and ')' in rest:
            id_part = rest.split('(')[0].strip()
            user_part = rest.split('(')[1].split(')')[0].strip()
            return admin, id_part, user_part
        else:
            return admin, rest, None
    except:
        return admin_str, None, None

def add_reason_status(df):
    """Add Reason Status column"""
    df['Reason Status'] = df['REASON'].apply(
        lambda x: 'WITH REASON' if pd.notna(x) and str(x).strip() != '' else 'NO REASON'
    )
    return df

def add_publish_status(df):
    """Add Publish Status based on ROSTER DATE"""
    def get_last_day_of_month(date):
        if date.month == 12:
            last_day = pd.Timestamp(year=date.year + 1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            last_day = pd.Timestamp(year=date.year, month=date.month + 1, day=1) - pd.Timedelta(days=1)
        return last_day
    
    df['Publish Status'] = df['ROSTER DATE'].apply(
        lambda x: 'Belum Publish' if x >= get_last_day_of_month(x) else 'Sudah Publish'
    )
    return df

def convert_utc_to_wib(utc_time):
    """Convert UTC to WIB (UTC+7)"""
    if pd.isna(utc_time):
        return None
    try:
        if isinstance(utc_time, str):
            utc_time = pd.to_datetime(utc_time)
        wib_time = utc_time + pd.Timedelta(hours=7)
        return wib_time
    except:
        return None

def add_std_local_time(df):
    """Add STD (Local Time) column"""
    df['STD (Local Time)'] = df['STD (UTC Time)'].apply(convert_utc_to_wib)
    return df

def add_user_status(df):
    """Add User Status based on ADMIN_USER and ADMIN_ID codes"""
    crew_training = {83118188, 240951, 241140, 146829, 171915, 150292, 242339, 154327, 242344, 242340, 
                     240168, 241432, 147875, 241435, 241482, 240952, 240953, 240954, 240957, 242328}
    crew_control = {84116714, 'M14647', 82088093, 151122, 242332, 82120906, 82102045, 242333, 252000, 153009, 
                    84122780, 240432, 242335, 241794, 134741, 82116818, 134744, 240431, 242344, 150283, 
                    242342, 82104894, 241169, 240723, 242334, 84104580, 220260, 252403}
    tracking = {84120306, 220515, 82104894, 240626, 252003, 251997, 252004, 240738, 241201, 84103500, 
                242338, 242329, 221399, 84120287, 84101641, 143516, 252002, 240628, 221027, 241797, 240627}
    paxlist = {84052867, 140108, 82119055, 150296, 151118, 135254, 82119055, 147426, 142543}
    
    def determine_status(admin_id):
        # try:
        #     # Try to convert to int for comparison
        #     user_int = int(admin_user) if pd.notna(admin_user) else None
        #     if user_int in crew_training:
        #         return 'Crew Training'
        #     if user_int in crew_admin:
        #         return 'Crew Admin'
        # except:
        #     pass
        
        try:
            admin_id_int = int(admin_id) if pd.notna(admin_id) else None
            if admin_id_int in crew_training:
                return 'Crew Training'
            if admin_id_int in crew_control:
                return 'Crew Control'
            if admin_id_int in tracking:
                return 'Tracking'
            if admin_id_int in paxlist:
                return 'Paxlist'
        except:
            try:
                if admin_id in crew_training:
                    return 'Crew Training'
                if admin_id in crew_control:
                    return 'Crew Control'
                if admin_id in tracking:
                    return 'Tracking'
                if admin_id in paxlist:
                    return 'Paxlist'
            except:
                pass
        
        return 'OTHER'
    
    df['User Status'] = df.apply(lambda row: determine_status(row['ADMIN_ID']), axis=1)
    return df

def add_kategori(df):
    """Add Kategori based on conditions"""
    def determine_kategori(row):
        action_date = pd.to_datetime(row['ACTION TIME (CGK Time)']).date()
        std_date = pd.to_datetime(row['STD (Local Time)']).date()
        user_status = row['User Status']

        # Hitung selisih tanggal
        selisih_hari = (std_date - action_date).days

        # Logika kategori
        if action_date == std_date and user_status == 'Tracking':
            return 'ACTUAL'
        elif action_date < std_date and user_status == 'Crew Control' and selisih_hari == 1:
            return 'FINAL'
        elif action_date < std_date and user_status == 'Crew Control':
            return 'PLAN'
        else:
            return 'OTHER'

    df['Kategori'] = df.apply(determine_kategori, axis=1)
    return df

def clean_reason_column(reason_str):
    """Clean REASON column with refined number-prefix and suffix rules"""
    if pd.isna(reason_str):
        return reason_str

    try:
        reason_str = str(reason_str).strip()

        # Hapus bagian setelah ' - '
        if ' - ' in reason_str:
            reason_str = reason_str.split(' - ')[0].strip()

        # Jika diawali "0." atau "2." → hapus seluruh prefix
        if re.match(r'^[0-9]+\.', reason_str):
            # Kalau setelah titik ada satu digit lalu spasi → ambil digit tsb
            # Contoh: "0.1 LANDING..." → ubah jadi "1 LANDING..."
            if re.match(r'^[0-9]+\.[0-9]+\s+', reason_str):
                reason_str = re.sub(r'^[0-9]+\.([0-9]+)\s+', r'\1 ', reason_str)
            else:
                # Contoh: "2.CHG ..." atau "0.CHG ..." → hapus semuanya
                reason_str = re.sub(r'^[0-9]+\.\s*', '', reason_str)

        return reason_str.strip()

    except:
        return reason_str

def clean_data(df):
    """Clean data by removing duplicates and invalid rows - DILAKUKAN SEBELUM PROCESSING"""
    # Clean REASON column first (remove ' - USER' suffix)
    df['REASON'] = df['REASON'].apply(clean_reason_column)
    
    # Remove duplicates based on specified columns
    df = df.drop_duplicates(subset=['ID', 'NAME', 'REASON', 'ACTIVITY BEFORE', 'ACTIVITY AFTER'], keep='first')
    
    # Convert for date comparison
    df['ROSTER DATE'] = pd.to_datetime(df['ROSTER DATE'])
    df['STD (UTC Time)'] = pd.to_datetime(df['STD (UTC Time)'])
    
    # Temporarily convert STD UTC to get date for comparison
    df['STD_TEMP'] = df['STD (UTC Time)'].apply(lambda x: convert_utc_to_wib(x))
    df['ROSTER_DATE_ONLY'] = df['ROSTER DATE'].dt.date
    df['STD_DATE_ONLY'] = df['STD_TEMP'].dt.date
    
    # Remove rows where ROSTER DATE != STD (Local Time) date
    df = df[df['ROSTER_DATE_ONLY'] == df['STD_DATE_ONLY']].copy()
    df = df.drop(['STD_TEMP', 'ROSTER_DATE_ONLY', 'STD_DATE_ONLY'], axis=1)
    
    return df

def process_data(df):
    """Process data - DILAKUKAN SETELAH CLEANING"""
    # Split ADMIN column (create new columns, don't override ADMIN)
    admin_split = df['ADMIN'].apply(lambda x: pd.Series(parse_admin_column(x)))
    df['ADMIN_NAME'] = admin_split[0]
    df['ADMIN_ID'] = admin_split[1]
    df['ADMIN_USER'] = admin_split[2]
    
    # Add new columns
    df = add_reason_status(df)
    df = add_publish_status(df)
    df = add_std_local_time(df)
    df = add_user_status(df)
    df = add_kategori(df)
    
    return df

def to_excel(df):
    """Convert DataFrame to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    output.seek(0)
    return output

# ==================== MAIN APP ====================

# Header aplikasi
st.markdown("""
<div class="main-header">
    <h1 style="color: white;">📊 REASON Modification Analysis </h1>
    <p>Analyze Crew Roster Modification Log</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# Sidebar - File Upload
with st.sidebar:
    st.header("📁 File Management")
    num_files = st.number_input("Jumlah file Excel yang ingin digabungkan:", min_value=1, max_value=10, value=1)
    
    uploaded_files = []
    for i in range(num_files):
        uploaded_file = st.file_uploader(f"Upload file {i+1}:", type="xlsx", key=f"file_{i}")
        if uploaded_file:
            uploaded_files.append(uploaded_file)
    
    process_button = st.button("🔄 Proses Data", use_container_width=True)

# Initialize session state
if 'df_combined' not in st.session_state:
    st.session_state.df_combined = None
if 'df_cleaned' not in st.session_state:
    st.session_state.df_cleaned = None
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = None

# Process files - NEW WORKFLOW
if process_button and uploaded_files:
    with st.spinner("⏳ Memproses data..."):
        try:
            # STEP 1: Combine files
            st.info("📊 Step 1/3: Menggabungkan file...")
            dfs = [pd.read_excel(file) for file in uploaded_files]
            st.session_state.df_combined = pd.concat(dfs, ignore_index=True)
            st.success("✅ File berhasil digabungkan!")
            
            # STEP 2: Clean data
            st.info("🧹 Step 2/3: Membersihkan data...")
            st.session_state.df_cleaned = clean_data(st.session_state.df_combined.copy())
            st.success("✅ Data berhasil dibersihkan!")
            
            # STEP 3: Process data
            st.info("⚙️ Step 3/3: Memproses data otomatis...")
            st.session_state.df_processed = process_data(st.session_state.df_cleaned.copy())
            st.success("✅ Data berhasil diproses!")
            
            # Show summary
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Data Gabungan", len(st.session_state.df_combined))
            with col2:
                st.metric("Setelah Dibersihkan", len(st.session_state.df_cleaned))
            with col3:
                st.metric("Duplikat Dihapus", len(st.session_state.df_combined) - len(st.session_state.df_cleaned))
            st.markdown("---")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Main content
if st.session_state.df_processed is not None:
    df_processed = st.session_state.df_processed
    
    # Sidebar - Filters
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filter Data")
    
    companies = df_processed['COMPANY'].unique()
    selected_companies = st.sidebar.multiselect("COMPANY:", companies, default=companies)
    
    kategori_list = df_processed['Kategori'].unique()
    selected_kategori = st.sidebar.multiselect("Kategori:", kategori_list, default=kategori_list)
    
    user_status_list = df_processed['User Status'].unique()
    selected_user_status = st.sidebar.multiselect("User Status:", user_status_list, default=user_status_list)
    
    reason_status_list = df_processed['Reason Status'].unique()
    selected_reason_status = st.sidebar.multiselect("Reason Status:", reason_status_list, default=reason_status_list)
    
    publish_status_list = df_processed['Publish Status'].unique()
    selected_publish_status = st.sidebar.multiselect("Publish Status:", publish_status_list, default=publish_status_list)
    
    # Apply filters
    df_filtered = df_processed[
        (df_processed['COMPANY'].isin(selected_companies)) &
        (df_processed['Kategori'].isin(selected_kategori)) &
        (df_processed['User Status'].isin(selected_user_status)) &
        (df_processed['Reason Status'].isin(selected_reason_status)) &
        (df_processed['Publish Status'].isin(selected_publish_status))
    ]
    
    # Statistics & Metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Records", len(df_filtered))
    with col2:
        with_reason = len(df_filtered[df_filtered['Reason Status'] == 'WITH REASON'])
        st.metric("With Reason", with_reason)
    with col3:
        no_reason = len(df_filtered[df_filtered['Reason Status'] == 'NO REASON'])
        st.metric("No Reason", no_reason)
    with col4:
        actual = len(df_filtered[df_filtered['Kategori'] == 'ACTUAL'])
        st.metric("ACTUAL", actual)
    with col5:
        plan = len(df_filtered[df_filtered['Kategori'] == 'PLAN'])
        st.metric("PLAN", plan)
    with col6:
        final = len(df_filtered[df_filtered['Kategori'] == 'FINAL'])
        st.metric("FINAL", final)
    
    st.markdown("---")
    
    # Visualizations
    col_left, col_right = st.columns(2)
    
    # Reason Distribution
    with col_left:
        st.subheader("📊 Distribusi REASON")
        reason_counts = df_filtered['Reason Status'].value_counts()
        fig_reason = px.pie(
            values=reason_counts.values,
            names=reason_counts.index,
            title="Reason Status Distribution",
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        fig_reason.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_reason, use_container_width=True)
    
    # Kategori Distribution
    with col_right:
        st.subheader("📈 Distribusi Kategori")
        kategori_counts = df_filtered['Kategori'].value_counts()
        fig_kategori = px.bar(
            x=kategori_counts.index,
            y=kategori_counts.values,
            title="Kategori Distribution",
            labels={'x': 'Kategori', 'y': 'Count'},
            color=kategori_counts.index,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_kategori.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_kategori, use_container_width=True)
    
    # REASON breakdown
    col_left2, col_right2 = st.columns(2)
    
    with col_left2:
        st.subheader("🔤 Top 5 REASON")
        reason_breakdown = df_filtered['REASON'].value_counts().head(5).sort_values(ascending=True)
        reason_percentage = (reason_breakdown / reason_breakdown.sum() * 100).round(2)
        fig_reason_breakdown = px.bar(
            x=reason_percentage.values,
            y=reason_percentage.index,
            orientation='h',
            title="Top 5 REASON (%)",
            labels={'x': 'Percentage (%)', 'y': 'REASON'},
            text=reason_percentage.values
        )
        fig_reason_breakdown.update_traces(textposition='outside', texttemplate='%{text:.2f}%')
        fig_reason_breakdown.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_reason_breakdown, use_container_width=True)
    
    with col_right2:
        st.subheader("👥 User Status Distribution")
        user_status_counts = df_filtered['User Status'].value_counts()
        fig_user_status = px.bar(
            x=user_status_counts.index,
            y=user_status_counts.values,
            title="User Status Distribution",
            labels={'x': 'User Status', 'y': 'Count'},
            color=user_status_counts.index,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_user_status.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_user_status, use_container_width=True)
    
    st.markdown("---")
    
    # Detailed Statistics
    st.subheader("📋 Statistik Detail berdasarkan REASON")
    
    reason_stats = df_filtered.groupby('REASON').agg({
        'ID': 'count',
        'Kategori': lambda x: (x == 'ACTUAL').sum(),
        'User Status': lambda x: (x == 'Crew Control').sum()
    }).rename(columns={'ID': 'Total', 'Kategori': 'ACTUAL Count', 'User Status': 'Crew Control Count'})
    reason_stats['Percentage'] = (reason_stats['Total'] / reason_stats['Total'].sum() * 100).round(2)
    reason_stats = reason_stats.sort_values('Total', ascending=False)
    
    st.dataframe(reason_stats, use_container_width=True)
    
    st.markdown("---")
    
    # Detailed Data Table
    st.subheader("📑 Detail Data")
    
    display_columns = ['ID', 'NAME', 'COMPANY', 'ROSTER DATE', 'ACTIVITY', 'REASON', 
                       'STD (Local Time)', 'ACTION TIME (CGK Time)', 'User Status', 
                       'Kategori', 'Reason Status', 'Publish Status']
    
    available_columns = [col for col in display_columns if col in df_filtered.columns]
    df_display = df_filtered[available_columns].copy()
    
    st.dataframe(df_display, use_container_width=True, height=400)
    
    st.markdown("---")
    
    # Download button
    st.subheader("📥 Download Data")
    col_down1, col_down2 = st.columns(2)
    
    with col_down1:
        # Download cleaned data only
        excel_cleaned = to_excel(st.session_state.df_cleaned)
        st.download_button(
            label="⬇️ Download Data Dibersihkan",
            data=excel_cleaned,
            file_name=f"REASON_Data_Dibersihkan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col_down2:
        # Download processed data
        excel_file = to_excel(df_filtered)
        st.download_button(
            label="⬇️ Download Data Hasil Proses Lengkap",
            data=excel_file,
            file_name=f"REASON_Analysis_NEW_CATEGORY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

else:

    st.info("👈 Silakan upload file Excel di sidebar untuk memulai analisis")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Crew Roster Modification Log Analysis Tool</p>
    <p><small>© Maurino Audrian Putra</small></p>
</div>

""", unsafe_allow_html=True)




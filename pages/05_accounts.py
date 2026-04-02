import streamlit as st
import pandas as pd
import re
import os
import datetime

st.set_page_config(page_title="미수금/미지급금 관리", page_icon="💰", layout="wide")

# -----------------------------------------------------------------------------
# [로직] 데이터 처리 및 연체 계산 함수
# -----------------------------------------------------------------------------
def process_data(df_raw, ref_date, mode="매출업체"):
    try:
        # 헤더 위치 탐색 ('업체구분' 문자가 있는 행 찾기)
        header_idx = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains('업체구분').any(), axis=1)].index
        if len(header_idx) > 0:
            idx = header_idx[0]
            df = df_raw.iloc[idx+1:].copy()
            df.columns = df_raw.iloc[idx].astype(str).str.strip()
        else:
            df = df_raw.copy()
            
        # 컬럼명 강제 지정
        df.columns = ['업체구분', '업체', '결제금액'] + list(df.columns[3:])
        df['업체구분'] = df['업체구분'].ffill()
        
        # 선택한 모드(매출/매입) 필터링 및 요약행 제거
        df_target = df[df['업체구분'] == mode].copy()
        df_target = df_target.dropna(subset=['업체'])
        df_target = df_target[~df_target['업체'].astype(str).str.contains('요약')]
        
        # 금액 숫자 변환 (백만 원 단위)
        df_target['결제금액'] = df_target['결제금액'].astype(str).str.replace(',', '').str.replace('₩', '').str.strip()
        df_target['금액_백만'] = pd.to_numeric(df_target['결제금액'], errors='coerce') / 1_000_000
        df_target = df_target.dropna(subset=['금액_백만'])

        # 업체명과 YYMM 분리
        def extract_info(val):
            val_str = str(val).strip()
            match = re.search(r'^(.*?)(\d{4})$', val_str)
            if match: return match.group(1).strip(), match.group(2)
            return val_str, None
            
        df_target[['거래처명', 'YYMM']] = df_target['업체'].apply(lambda x: pd.Series(extract_info(x)))
        
        # 경과 개월 계산
        def calc_delay(yymm):
            if not yymm: return 0
            y = 2000 + int(yymm[:2])
            m = int(yymm[2:])
            delay = (ref_date.year - y) * 12 + (ref_date.month - m)
            return delay if delay >= 0 else 0
            
        df_target['연체개월'] = df_target['YYMM'].apply(calc_delay)
        
        result = []
        for name, group in df_target.groupby('거래처명'):
            total_amt = group['금액_백만'].sum()
            if total_amt <= 0: continue
            
            max_delay = group['연체개월'].max()
            note_parts = []
            for d in sorted(group['연체개월'].unique(), reverse=True):
                amt = group[group['연체개월'] == d]['금액_백만'].sum()
                if amt > 0:
                    label = f"{int(d)}개월 초과" if d > 1 else "1개월 이하"
                    note_parts.append(f"{label}: {amt:.1f}")
                    
            result.append({
                '거래처명': name,
                '총액': round(total_amt, 1),
                '최대 경과': f"{int(max_delay)}개월" if max_delay > 0 else "1개월",
                '상세 비고': " / ".join(note_parts),
                '_sort': total_amt
            })
            
        return pd.DataFrame(result).sort_values('_sort', ascending=False).drop(columns=['_sort']) if result else pd.DataFrame()
    except: 
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# [UI] 화면 구성
# -----------------------------------------------------------------------------
st.title("💰 매입/매출 잔고 관리")

tab1, tab2 = st.tabs(["🔴 미수금 (매출업체)", "🔵 미지급금 (매입업체)"])

# 공통 설정
col_d, col_f = st.columns([1, 1])
with col_d: 
    ref_date = st.date_input("🗓️ 계산 기준일자", datetime.date.today())
with col_f: 
    uploaded_file = st.file_uploader("📂 장부 엑셀 업로드 (accounts.xlsx)", type=['xlsx'])

# 파일 로드 (accounts.xlsx 기준)
df_raw = None
if uploaded_file: 
    df_raw = pd.read_excel(uploaded_file, header=None)
elif os.path.exists('accounts.xlsx'): 
    df_raw = pd.read_excel('accounts.xlsx', header=None)

def show_table(data, title, date_str):
    if data.empty:
        st.warning(f"표시할 {title} 데이터가 없습니다.")
        return
    
    st.markdown(f"<div style='text-align: right; font-weight: bold;'>{date_str}</div>", unsafe_allow_html=True)
    
    html = f"""
    <style>
        .r-table {{ width: 100%; border-collapse: collapse; font-size: 14px; border-top: 2px solid #333; }}
        .r-table th {{ background: #f8f9fa; border-bottom: 1px solid #ddd; padding: 10px; text-align: left; }}
        .r-table td {{ border-bottom: 1px solid #eee; padding: 8px 10px; }}
    </style>
    <table class="r-table">
        <thead><tr><th>거래처명</th><th>금액(백만)</th><th>최대 경과</th><th>상세 내역</th></tr></thead>
        <tbody>
    """
    for _, r in data.iterrows():
        html += f"<tr><td><b>{r['거래처명']}</b></td><td><b>{r['총액']:.1f}</b></td><td>{r['최대 경과']}</td><td>{r['상세 비고']}</td></tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"### 🚩 {title} 합계: {data['총액'].sum():.1f} 백만 원")

if df_raw is not None:
    date_label = f"({ref_date.month}월 {ref_date.day}일 기준, 단위:백만 원)"
    with tab1:
        res = process_data(df_raw, ref_date, "매출업체")
        show_table(res, "총 미수금", date_label)
    with tab2:
        res = process_data(df_raw, ref_date, "매입업체")
        show_table(res, "총 미지급금", date_label)
else:
    st.info("파일 목록에 'accounts.xlsx'를 올리거나 업로드 박스를 이용하세요.")

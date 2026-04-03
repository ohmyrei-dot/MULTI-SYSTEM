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
        # 변경된 양식(첫 번째 행이 컬럼명)에 맞춰 데이터 정리
        df = df_raw.copy()
        
        # 첫 번째 열에 "매입/매출업체"가 있는 행을 헤더로 지정
        header_idx = df[df.apply(lambda r: r.astype(str).str.contains('매입/매출업체').any(), axis=1)].index
        if len(header_idx) > 0:
            idx = header_idx[0]
            df.columns = df.iloc[idx].astype(str).str.strip()
            df = df.iloc[idx+1:].copy()
        
        # 필요한 열 이름이 있는지 확인 후 필터링
        if '매입/매출업체' not in df.columns or '업체' not in df.columns or '합계 : 결제금액' not in df.columns:
            return pd.DataFrame() # 열 이름이 다르면 빈 데이터 반환
            
        df = df.rename(columns={'매입/매출업체': '업체구분', '합계 : 결제금액': '결제금액'})
        df['업체구분'] = df['업체구분'].ffill()
        
        df_target = df[df['업체구분'] == mode].copy()
        df_target = df_target.dropna(subset=['업체'])
        df_target = df_target[~df_target['업체'].astype(str).str.contains('요약')]
        
        df_target['결제금액'] = df_target['결제금액'].astype(str).str.replace(',', '').str.replace('₩', '').str.strip()
        df_target['금액_백만'] = pd.to_numeric(df_target['결제금액'], errors='coerce') / 1_000_000
        df_target = df_target.dropna(subset=['금액_백만'])

        def extract_info(val):
            val_str = str(val).strip()
            match = re.search(r'^(.*?)(\d{4})$', val_str)
            if match: return match.group(1).strip(), match.group(2)
            return val_str, None
            
        df_target[['거래처명', 'YYMM']] = df_target['업체'].apply(lambda x: pd.Series(extract_info(x)))
        
        def calc_delay(yymm):
            if not yymm: return 0
            y = 2000 + int(yymm[:2])
            m = int(yymm[2:])
            # 당월을 1개월 차로 계산하기 위해 + 1 추가
            delay = (ref_date.year - y) * 12 + (ref_date.month - m) + 1
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

# 기준일자 (오류 원인이었던 달력 부분, 안내 문구 추가)
ref_date = st.date_input("🗓️ 계산 기준일자 (💡 엑셀 데이터 시점에 맞게 변경해야 개월 수가 정확히 계산됩니다)", datetime.date.today())
st.markdown("---")

tab1, tab2 = st.tabs(["🔴 미수금 (매출업체)", "🔵 미지급금 (매입업체)"])

# 폴더의 accounts.xlsx 파일만 자동 로드 (업로드 위젯 삭제)
df_raw = None
if os.path.exists('accounts.xlsx'): 
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
    st.error("🚨 폴더에 'accounts.xlsx' 파일이 없습니다. 파일을 업로드해주세요.")

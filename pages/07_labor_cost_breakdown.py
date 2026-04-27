import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="Labor Cost Breakdown", page_icon="🕵️‍♂️", layout="wide")

# -----------------------------------------------------------------------------
# [데이터 강제 로드 로직] 세션에 데이터가 없으면 불러오기
# -----------------------------------------------------------------------------
file_path = 'price_list.xlsx'
if 'df_purch' not in st.session_state:
    if os.path.exists(file_path):
        st.session_state['df_purch'] = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
    else:
        st.error(f"🚨 '{file_path}' 파일이 존재하지 않습니다.")
        st.stop()

# -----------------------------------------------------------------------------
# [Helper] 숫자 포맷팅 및 정규식 추출
# -----------------------------------------------------------------------------
def fmt(val):
    if pd.isna(val) or val is None: return "-"
    val = round(float(val), 1)
    return f"{int(val):,}" if val.is_integer() else f"{val:,.1f}"

def extract_width(spec):
    s = str(spec).replace(' ', '').lower()
    # 1.5*50, 2x50 등에서 *나 x 앞의 숫자를 폭으로 추출
    m = re.search(r'(\d+(?:\.\d+)?)[*x]', s)
    if m: return float(m.group(1))
    # '2' 등 단일 숫자로만 적혀있을 경우 대비
    m2 = re.search(r'^(\d+(?:\.\d+)?)$', s)
    if m2: return float(m2.group(1))
    return None

def extract_thickness(note):
    # '8mm', '10 mm가공' 등에서 로프 두께 추출
    m = re.search(r'(\d+)\s*mm', str(note).lower())
    if m: return int(m.group(1))
    return 0

# -----------------------------------------------------------------------------
# 메인 로직
# -----------------------------------------------------------------------------
st.title("🕵️‍♂️ Labor Cost Breakdown")
st.markdown("매입업체의 폭(Width)별 매입단가를 분석하여, **원가(망+로프)를 제외한 순수 가공 인건비**가 어떻게 변하는지 추적합니다.")

try:
    df_purch = st.session_state['df_purch'].copy()
    
    # 컬럼 표준화
    vendor_col = next((c for c in df_purch.columns if '매입업체' in str(c)), '매입업체')
    price_col = next((c for c in df_purch.columns if '단가' in str(c)), '현재매입단가')
    
    note_col = '비고 1' if '비고 1' in df_purch.columns else '비고'
    if note_col not in df_purch.columns: 
        df_purch[note_col] = ""
    df_purch[note_col] = df_purch[note_col].fillna("").astype(str)
    
    if '규격' not in df_purch.columns:
        if '규격1' in df_purch.columns: df_purch['규격'] = df_purch['규격1']
        else: df_purch['규격'] = ""

    all_vendors = sorted(df_purch[vendor_col].dropna().unique().astype(str))
    
    # 1. 설정 영역
    st.subheader("1. 분석 조건 설정")
    c1, c2 = st.columns(2)
    with c1:
        sel_vendor = st.selectbox("🏢 분석할 매입업체 선택", all_vendors, index=all_vendors.index('경진') if '경진' in all_vendors else 0)
    with c2:
        sel_item = st.selectbox("🕸️ 안전망 종류 선택", ['안전망2cm', '안전망2cm KS망', '안전망1cm', '안전망1cm KS망'])

    st.markdown("<br><b>⚙️ 기준 원자재 단가 (인건비 역산용)</b>", unsafe_allow_html=True)
    st.caption("해당 업체의 단가를 기본으로 불러오며, 없을 경우 수동으로 조정하여 시뮬레이션 할 수 있습니다.")
    
    # 띄어쓰기 무시하고 품목 매칭
    sel_item_clean = sel_item.replace(" ", "")
    df_v = df_purch[df_purch[vendor_col] == sel_vendor]
    df_v_matched = df_v[df_v['품목'].astype(str).str.replace(" ", "").str.contains(sel_item_clean, na=False)]
    
    # 미가공 단가 찾기
    net_base_row = df_v_matched[df_v_matched[note_col].str.contains('미가공', na=False)]
    default_net_price = float(net_base_row.iloc[0][price_col]) if not net_base_row.empty and pd.notna(net_base_row.iloc[0][price_col]) else 830.0

    # PP로프 단가 찾기 (기본값 설정)
    rope_base = {6: 12000, 8: 20000, 10: 30000, 12: 43000}
    
    r1, r2, r3, r4, r5 = st.columns(5)
    with r1:
        net_price = st.number_input(f"{sel_item} 미가공 (원/m²)", value=float(default_net_price), step=10.0)
    with r2:
        r_price_6 = st.number_input("6mm 로프 (200m/롤)", value=float(rope_base[6]), step=500.0)
    with r3:
        r_price_8 = st.number_input("8mm 로프 (200m/롤)", value=float(rope_base[8]), step=500.0)
    with r4:
        r_price_10 = st.number_input("10mm 로프 (200m/롤)", value=float(rope_base[10]), step=500.0)
    with r5:
        r_price_12 = st.number_input("12mm 로프 (200m/롤)", value=float(rope_base[12]), step=500.0)

    rope_prices = {6: r_price_6, 8: r_price_8, 10: r_price_10, 12: r_price_12}
    rope_length_per_roll = 126.0 # 50m 기준 1롤당 가공 로프 소요량

    st.divider()

    # 2. 데이터 추출 및 계산
    st.subheader(f"2. [{sel_vendor}] 인건비 구조 분석 결과")
    
    # 비고란에 '가공' 이라는 단어가 없어도 'mm' 숫자가 있으면 가공품으로 유연하게 인식
    def is_processed(note):
        note_str = str(note).lower()
        return bool(re.search(r'\d+\s*mm', note_str)) or '가공' in note_str and '미가공' not in note_str

    df_target = df_v_matched[df_v_matched[note_col].apply(is_processed)].copy()
    
    if df_target.empty:
        st.warning(f"선택한 업체({sel_vendor})의 {sel_item} 가공품 데이터가 없습니다. (엑셀 데이터 확인 필요)")
    else:
        results = []
        for _, row in df_target.iterrows():
            spec = row['규격']
            note = row[note_col]
            purchase_price = row[price_col]
            
            if pd.isna(purchase_price) or purchase_price == 0: continue
            
            width = extract_width(spec)
            thick = extract_thickness(note)
            
            if width is None or thick not in rope_prices: continue
            
            area = width * 50.0
            
            # 원가 계산
            net_cost_roll = area * net_price
            rope_cost_roll = (rope_prices[thick] / 200.0) * rope_length_per_roll
            total_cost_roll = net_cost_roll + rope_cost_roll
            
            # 매입총액 계산
            purchase_total_roll = area * purchase_price
            
            # 순수인건비 역산
            labor_roll = purchase_total_roll - total_cost_roll
            labor_m2 = labor_roll / area if area > 0 else 0
            
            results.append({
                '폭(m)': width,
                '두께(mm)': thick,
                '매입단가 (m²)': purchase_price,
                '1롤 면적 (m²)': area,
                '망+로프 원가 (1롤)': total_cost_roll,
                '매입총액 (1롤)': purchase_total_roll,
                '순수인건비 (m²)': labor_m2,
                '순수인건비 (1롤)': labor_roll
            })

        if not results:
            st.warning("분석 가능한 규격(폭 숫자, mm두께) 데이터가 추출되지 않았습니다.")
        else:
            df_res = pd.DataFrame(results)
            df_res = df_res.sort_values(by=['두께(mm)', '폭(m)']).reset_index(drop=True)
            
            # 출력 포맷팅
            df_show = df_res.copy()
            df_show['폭(m)'] = df_show['폭(m)'].apply(lambda x: f"{x:g}m")
            df_show['두께(mm)'] = df_show['두께(mm)'].apply(lambda x: f"{x}mm")
            df_show['매입단가 (m²)'] = df_show['매입단가 (m²)'].apply(lambda x: f"{int(x):,}원")
            df_show['1롤 면적 (m²)'] = df_show['1롤 면적 (m²)'].apply(lambda x: f"{x:g}m²")
            df_show['망+로프 원가 (1롤)'] = df_show['망+로프 원가 (1롤)'].apply(lambda x: f"{int(x):,}원")
            df_show['매입총액 (1롤)'] = df_show['매입총액 (1롤)'].apply(lambda x: f"{int(x):,}원")
            
            df_show['순수인건비 (m²)'] = df_show['순수인건비 (m²)'].apply(lambda x: f"⚠️ {int(x):,}원")
            df_show['순수인건비 (1롤)'] = df_show['순수인건비 (1롤)'].apply(lambda x: f"🔥 {int(x):,}원")
            
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
            st.info("""
            💡 **분석 포인트**
            - 매입단가(m²)가 폭에 상관없이 일정하다면, 우측의 **'순수인건비 (1롤)'이 폭이 넓어질수록 눈덩이처럼 증가**하는 구조임을 확인할 수 있습니다.
            """)

except Exception as e:
    st.error(f"오류 발생: {e}")

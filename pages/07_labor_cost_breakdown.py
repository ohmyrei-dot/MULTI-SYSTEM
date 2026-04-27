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
        sel_vendor = st.selectbox("🏢 분석할 매입업체 선택", all_vendors, index=all_vendors.index('태양산자') if '태양산자' in all_vendors else 0)
    with c2:
        sel_item = st.selectbox("🕸️ 안전망 종류 선택", ['안전망2cm', '안전망2cm KS망', '안전망1cm', '안전망1cm KS망'])

    st.markdown("<br><b>⚙️ 기준 원자재 단가 (인건비 역산용)</b>", unsafe_allow_html=True)
    st.caption("해당 업체의 미가공 단가를 자동으로 불러옵니다. (없으면 기본값 적용)")
    
    # --- 한층 더 유연해진 필터링 로직 ---
    target_cm = "2cm" if "2cm" in sel_item else "1cm"
    target_ks = "KS" in sel_item

    def is_target_item(row):
        item_str = str(row['품목']).replace(" ", "").upper()
        full_str = (str(row['품목']) + "|" + str(row['규격']) + "|" + str(row[note_col])).replace(" ", "").upper()
        
        # 1cm / 2cm 유연한 확인 ('안전망'만 적혀있으면 2cm로 간주)
        if target_cm == "2cm":
            if "1CM" in item_str: return False
            if "2CM" not in item_str and "안전망" not in item_str: return False
        else:
            if "1CM" not in item_str: return False
        
        # KS 여부 확인
        has_ks = 'KS' in full_str
        if target_ks and not has_ks: return False
        if not target_ks and has_ks: return False
        
        return True

    df_v = df_purch[df_purch[vendor_col] == sel_vendor].copy()
    df_v_matched = df_v[df_v.apply(is_target_item, axis=1)].copy()
    
    # 미가공 단가 추출 ('미가공' 단어가 있거나, 비고가 완전히 비어있는 행을 미가공으로 추정)
    def is_net_only(r):
        s = (str(r['규격']) + str(r[note_col])).replace(' ', '').lower()
        return '미가공' in s or (not re.search(r'\d+mm', s) and '가공' not in s)

    net_base_row = df_v_matched[df_v_matched.apply(is_net_only, axis=1)]
    default_net_price = float(net_base_row.iloc[0][price_col]) if not net_base_row.empty and pd.notna(net_base_row.iloc[0][price_col]) else 830.0

    # PP로프 단가 설정
    rope_base = {6: 12000, 8: 20000, 10: 30000, 12: 43000}
    
    r1, r2, r3, r4, r5 = st.columns(5)
    with r1: net_price = st.number_input(f"{sel_item} 미가공 (원/m²)", value=float(default_net_price), step=10.0)
    with r2: r_price_6 = st.number_input("6mm 로프 (200m/롤)", value=float(rope_base[6]), step=500.0)
    with r3: r_price_8 = st.number_input("8mm 로프 (200m/롤)", value=float(rope_base[8]), step=500.0)
    with r4: r_price_10 = st.number_input("10mm 로프 (200m/롤)", value=float(rope_base[10]), step=500.0)
    with r5: r_price_12 = st.number_input("12mm 로프 (200m/롤)", value=float(rope_base[12]), step=500.0)

    rope_prices = {6: r_price_6, 8: r_price_8, 10: r_price_10, 12: r_price_12}
    rope_length_per_roll = 126.0 # 50m 기준 1롤당 가공 로프 소요량

    st.divider()

    # 2. 데이터 추출 및 계산
    st.subheader(f"2. [{sel_vendor}] 인건비 구조 분석 결과")
    
    def extract_details(row):
        full_str = (str(row['규격']) + "|" + str(row[note_col])).replace(" ", "").lower()
        
        # 로프 두께 파악 (무조건 mm 앞의 숫자)
        thick = None
        t_match = re.search(r'(\d+)mm', full_str)
        if t_match: thick = int(t_match.group(1))
        
        # 폭(Width) 파악 ('1*50', '1.5', '2.0X50' 등 다양한 형식 대응)
        width = None
        spec_str = str(row['규격']).replace(" ", "").lower()
        w_match = re.search(r'(\d+(?:\.\d+)?)[*x]50', spec_str)
        if w_match: width = float(w_match.group(1))
        else:
            w_match2 = re.search(r'^(\d+(?:\.\d+)?)$', spec_str)
            if w_match2: width = float(w_match2.group(1))
            
        return pd.Series({'width': width, 'thick': thick})

    if not df_v_matched.empty:
        details = df_v_matched.apply(extract_details, axis=1)
        df_target = pd.concat([df_v_matched, details], axis=1)
        
        # 두께(mm)와 폭(m)이 모두 추출된 데이터만 '가공품'으로 간주
        df_target = df_target[(df_target['width'].notna()) & (df_target['thick'].isin(rope_prices.keys()))]
    else:
        df_target = pd.DataFrame()

    if df_target.empty:
        st.warning(f"선택한 업체({sel_vendor})의 {sel_item} 데이터에서 폭과 로프 두께(mm)를 확인할 수 없습니다.")
        st.info("💡 엑셀의 '규격' 칸에 폭이 (예: 1, 1.5, 2*50) 적혀있고, '비고' 칸에 (예: 8mm, 10mm가공)이 명시되어 있는지 확인해주세요.")
    else:
        results = []
        for _, row in df_target.iterrows():
            purchase_price = row[price_col]
            if pd.isna(purchase_price) or purchase_price == 0: continue
            
            width = row['width']
            thick = row['thick']
            area = width * 50.0
            
            # 원가 및 인건비 계산
            net_cost_roll = area * net_price
            rope_cost_roll = (rope_prices[thick] / 200.0) * rope_length_per_roll
            total_cost_roll = net_cost_roll + rope_cost_roll
            
            purchase_total_roll = area * purchase_price
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
            st.warning("계산 가능한 단가 데이터가 없습니다.")
        else:
            df_res = pd.DataFrame(results)
            df_res = df_res.sort_values(by=['폭(m)', '두께(mm)']).reset_index(drop=True)
            
            # -------------------------------------------------------------
            # 📊 피벗 테이블 (폭 vs 두께별 인건비) - 유저 요청 핵심 기능
            # -------------------------------------------------------------
            st.markdown("#### 📊 폭 vs 로프두께별 [1롤당 순수인건비] 비교표")
            
            # 폭을 행(index)으로, 두께를 열(columns)로 피벗
            df_pivot = df_res.pivot_table(index='폭(m)', columns='두께(mm)', values='순수인건비 (1롤)', aggfunc='first')
            
            # 인덱스 및 컬럼명 꾸미기
            df_pivot.index = df_pivot.index.map(lambda x: f"{x:g}m")
            df_pivot.columns = [f"{int(c)}mm 가공" for c in df_pivot.columns]
            
            # 하이라이팅 포맷 적용
            st.dataframe(
                df_pivot.style.format(lambda x: f"🔥 {int(x):,}원" if pd.notna(x) else "-")
                              .background_gradient(cmap='Reds', axis=None), 
                use_container_width=True
            )
            
            # -------------------------------------------------------------
            # 📝 상세 분석 데이터
            # -------------------------------------------------------------
            st.markdown("<br>#### 📝 상세 분석 데이터", unsafe_allow_html=True)
            
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
            - 태양산자처럼 매입단가(m²)가 폭에 상관없이 일정하다면, 위의 표에서 **폭이 넓어질수록(아래로 갈수록) 1롤당 순수인건비가 눈덩이처럼 폭발적으로 증가**하는 것을 직관적으로 확인할 수 있습니다.
            """)

except Exception as e:
    st.error(f"오류 발생: {e}")

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="견적서 작성", page_icon="📄", layout="wide")

# 1. 기본 단가 리스트 (하드코딩)
DEFAULT_PRICES = [
    {"번호": 1, "품명": "안전망 2cm", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 700, "금액(원)": None, "비고": ""},
    {"번호": 2, "품명": "안전망 2cm", "규격": "6mm가공", "단위": "m2", "수량": None, "단가(원)": 1050, "금액(원)": None, "비고": ""},
    {"번호": 3, "품명": "안전망 2cm", "규격": "8mm가공", "단위": "m2", "수량": None, "단가(원)": 1100, "금액(원)": None, "비고": ""},
    {"번호": 4, "품명": "안전망 2cm", "규격": "10mm가공", "단위": "m2", "수량": None, "단가(원)": 1250, "금액(원)": None, "비고": ""},
    {"번호": 5, "품명": "안전망 2cm 방염", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 900, "금액(원)": None, "비고": ""},
    {"번호": 6, "품명": "안전망 2cm 방염", "규격": "6mm가공", "단위": "m2", "수량": None, "단가(원)": 1250, "금액(원)": None, "비고": ""},
    {"번호": 7, "품명": "안전망 2cm 방염", "규격": "8mm가공", "단위": "m2", "수량": None, "단가(원)": 1300, "금액(원)": None, "비고": ""},
    {"번호": 8, "품명": "안전망 2cm 방염", "규격": "10mm가공", "단위": "m2", "수량": None, "단가(원)": 1450, "금액(원)": None, "비고": ""},
    {"번호": 9, "품명": "안전망 1cm", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 1400, "금액(원)": None, "비고": ""},
    {"번호": 10, "품명": "안전망 1cm", "규격": "가공품", "단위": "m2", "수량": None, "단가(원)": 1650, "금액(원)": None, "비고": ""},
    {"번호": 11, "품명": "안전망 1cm 방염", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 1800, "금액(원)": None, "비고": ""},
    {"번호": 12, "품명": "안전망 1cm 방염", "규격": "가공품", "단위": "m2", "수량": None, "단가(원)": 2050, "금액(원)": None, "비고": ""},
    {"번호": 13, "품명": "멀티망", "규격": "1200D", "단위": "m2", "수량": None, "단가(원)": 420, "금액(원)": None, "비고": ""},
    {"번호": 14, "품명": "럿셀망", "규격": "1.2", "단위": "R/L", "수량": None, "단가(원)": 16000, "금액(원)": None, "비고": ""},
    {"번호": 15, "품명": "럿셀망", "규격": "1.5", "단위": "R/L", "수량": None, "단가(원)": 20000, "금액(원)": None, "비고": ""},
    {"번호": 16, "품명": "럿셀망", "규격": "1.8", "단위": "R/L", "수량": None, "단가(원)": 25000, "금액(원)": None, "비고": ""},
    {"번호": 17, "품명": "pp로프(400m)", "규격": "5mm", "단위": "R/L", "수량": None, "단가(원)": 14000, "금액(원)": None, "비고": ""},
    {"번호": 18, "품명": "pp로프(200m)", "규격": "6mm", "단위": "R/L", "수량": None, "단가(원)": 11000, "금액(원)": None, "비고": ""},
    {"번호": 19, "품명": "pp로프(200m)", "규격": "8mm", "단위": "R/L", "수량": None, "단가(원)": 19000, "금액(원)": None, "비고": ""},
    {"번호": 20, "품명": "pp로프(200m)", "규격": "10mm", "단위": "R/L", "수량": None, "단가(원)": 29000, "금액(원)": None, "비고": ""},
    {"번호": 21, "품명": "pp로프(200m)", "규격": "12mm", "단위": "R/L", "수량": None, "단가(원)": 42000, "금액(원)": None, "비고": ""},
    {"번호": 22, "품명": "pp로프(200m)", "규격": "16mm", "단위": "R/L", "수량": None, "단가(원)": 74000, "금액(원)": None, "비고": ""},
    {"번호": 23, "품명": "와이어", "규격": "", "단위": "M", "수량": None, "단가(원)": 300, "금액(원)": None, "비고": ""},
    {"번호": 24, "품명": "와이어클립", "규격": "", "단위": "EA", "수량": None, "단가(원)": 130, "금액(원)": None, "비고": ""},
    {"번호": 25, "품명": "케이블타이", "규격": "270mm", "단위": "봉", "수량": None, "단가(원)": 15000, "금액(원)": None, "비고": ""}
]

def get_vendor_price(vendor_name, item_name, spec_name, default_price):
    if 'df_sales' not in st.session_state: return default_price
    df_sales = st.session_state['df_sales']
    
    vendor_col = next((c for c in df_sales.columns if '매출업체' in str(c) or '업체' in str(c)), None)
    if not vendor_col: return default_price
    
    df_v = df_sales[df_sales[vendor_col].astype(str) == vendor_name]
    if df_v.empty: return default_price
    
    clean_item = str(item_name).replace(" ", "").lower()
    clean_spec = str(spec_name).replace(" ", "").lower()
    
    for _, row in df_v.iterrows():
        db_item = str(row.get('품목', '')).replace(" ", "").lower()
        db_spec1 = str(row.get('규격1', row.get('규격', ''))).replace(" ", "").lower()
        
        if db_item in clean_item or clean_item in db_item:
            if clean_spec == "" or clean_spec in db_spec1 or db_spec1 in clean_spec:
                price_cols = [c for c in df_sales.columns if '단가' in c or '가격' in c]
                if price_cols:
                    try: return float(row[price_cols[0]])
                    except: pass
    return default_price

def load_initial_data(vendor_name):
    df = pd.DataFrame(DEFAULT_PRICES)
    df['기본단가'] = df['단가(원)'] # 숨김 처리용
    for idx in df.index:
        price = get_vendor_price(vendor_name, df.loc[idx, '품명'], df.loc[idx, '규격'], df.loc[idx, '단가(원)'])
        df.loc[idx, '단가(원)'] = price
        df.loc[idx, '기본단가'] = price
    return df

def apply_discount():
    rate = st.session_state.quote_discount
    df = st.session_state.quote_df
    for idx in df.index:
        base_p = df.loc[idx, '기본단가']
        if pd.notna(base_p):
            df.loc[idx, '단가(원)'] = int(float(base_p) * (1 + rate / 100))

def change_vendor():
    vendor = st.session_state.quote_vendor
    st.session_state.quote_df = load_initial_data(vendor)
    st.session_state.quote_discount = 0

# 메인 UI
st.title("📄 견적서 작성")
st.markdown("견적서를 작성하고 단가와 수량을 조절하여 총 합계를 계산하세요.")

vendor_list = ["경원안전"]
if 'df_sales' in st.session_state:
    df_sales = st.session_state['df_sales']
    v_col = next((c for c in df_sales.columns if '매출업체' in str(c) or '업체' in str(c)), None)
    if v_col:
        vendor_list = sorted(list(set(df_sales[v_col].dropna().astype(str))) + ["직접 입력"])
        if "경원안전" not in vendor_list: vendor_list.insert(0, "경원안전")

# 초기 세팅
if 'quote_vendor' not in st.session_state: st.session_state.quote_vendor = "경원안전"
if 'quote_df' not in st.session_state: st.session_state.quote_df = load_initial_data("경원안전")
if 'quote_discount' not in st.session_state: st.session_state.quote_discount = 0

c1, c2 = st.columns([1, 1])
with c1:
    st.selectbox("1️⃣ 수신처 (매출업체 선택)", vendor_list, index=vendor_list.index(st.session_state.quote_vendor) if st.session_state.quote_vendor in vendor_list else 0, key="quote_vendor", on_change=change_vendor)
with c2:
    st.number_input("2️⃣ 단가 일괄 조정 (%)", min_value=-100, max_value=100, value=st.session_state.quote_discount, step=5, key="quote_discount", on_change=apply_discount)

st.caption("💡 **수량**을 입력하면 금액이 자동 계산됩니다. 규격에 `10x20` 형식으로 입력하면 가로세로 면적이 수량에 곱해집니다.")

edited_df = st.data_editor(
    st.session_state.quote_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_order=["번호", "품명", "규격", "단위", "수량", "단가(원)", "금액(원)", "비고"],
    column_config={
        "번호": st.column_config.NumberColumn("번호", disabled=True, width="small"),
        "금액(원)": st.column_config.NumberColumn("금액(원)", disabled=True, format="%d"),
        "기본단가": None # 숨김
    }
)

# 3. 실시간 금액 계산 로직
changed = False
for idx in edited_df.index:
    qty = edited_df.loc[idx, '수량']
    price = edited_df.loc[idx, '단가(원)']
    item = str(edited_df.loc[idx, '품명'])
    spec = str(edited_df.loc[idx, '규격'])
    
    multiplier = 1.0
    if '럿셀망' in item:
        multiplier = 1.0
    elif any(x in item for x in ['안전망', '멀티망']):
        nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec)]
        if len(nums) >= 2: multiplier = nums[0] * nums[1]
        elif len(nums) == 1 and re.search(r'[xX*]', spec): multiplier = nums[0] # 가로세로 기호가 있을 때만 곱함
    elif any(x in item for x in ['와이어로프', '와이어클립']):
        nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec)]
        if nums and re.search(r'[mM미터]', spec): multiplier = nums[-1]
    
    try:
        if pd.notna(qty) and str(qty).strip() != "" and float(qty) > 0 and pd.notna(price):
            amt = float(qty) * float(price) * multiplier
            new_amt = int(amt)
            if edited_df.loc[idx, '금액(원)'] != new_amt:
                edited_df.loc[idx, '금액(원)'] = new_amt
                changed = True
        else:
            if pd.notna(edited_df.loc[idx, '금액(원)']):
                edited_df.loc[idx, '금액(원)'] = None
                changed = True
    except: pass

# 사용자가 단가를 직접 수정했을 경우 기본단가 동기화
for idx in edited_df.index:
    try:
        if idx in st.session_state.quote_df.index:
            if st.session_state.quote_df.loc[idx, '단가(원)'] != edited_df.loc[idx, '단가(원)']:
                edited_df.loc[idx, '기본단가'] = edited_df.loc[idx, '단가(원)']
                changed = True
    except: pass

if changed or not edited_df.equals(st.session_state.quote_df):
    st.session_state.quote_df = edited_df.copy()
    st.rerun()

st.divider()
total_sum = edited_df['금액(원)'].dropna().sum()
st.markdown(f"<h3 style='text-align: right;'>총 합계금액 : {int(total_sum):,} 원 (VAT 별도)</h3>", unsafe_allow_html=True)

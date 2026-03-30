import streamlit as st
import pandas as pd
import re
import datetime

st.set_page_config(page_title="견적서 작성", page_icon="📄", layout="wide")

# 1. 기본 단가 리스트 (하드코딩)
DEFAULT_PRICES = [
    {"번호": 1, "품명": "안전망2cm", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 750, "금액(원)": None, "비고": ""},
    {"번호": 2, "품명": "안전망2cm", "규격": "6mm가공", "단위": "m2", "수량": None, "단가(원)": 1100, "금액(원)": None, "비고": ""},
    {"번호": 3, "품명": "안전망2cm", "규격": "8mm가공", "단위": "m2", "수량": None, "단가(원)": 1150, "금액(원)": None, "비고": ""},
    {"번호": 4, "품명": "안전망2cm", "규격": "10mm가공", "단위": "m2", "수량": None, "단가(원)": 1300, "금액(원)": None, "비고": ""},
    {"번호": 5, "품명": "안전망2cm KS망", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 950, "금액(원)": None, "비고": ""},
    {"번호": 6, "품명": "안전망2cm KS망", "규격": "6mm가공", "단위": "m2", "수량": None, "단가(원)": 1300, "금액(원)": None, "비고": ""},
    {"번호": 7, "품명": "안전망2cm KS망", "규격": "8mm가공", "단위": "m2", "수량": None, "단가(원)": 1350, "금액(원)": None, "비고": ""},
    {"번호": 8, "품명": "안전망2cm KS망", "규격": "10mm가공", "단위": "m2", "수량": None, "단가(원)": 1500, "금액(원)": None, "비고": ""},
    {"번호": 9, "품명": "안전망1cm", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 1500, "금액(원)": None, "비고": ""},
    {"번호": 10, "품명": "안전망1cm", "규격": "가공품", "단위": "m2", "수량": None, "단가(원)": 1750, "금액(원)": None, "비고": ""},
    {"번호": 11, "품명": "안전망1cm KS망", "규격": "미가공", "단위": "m2", "수량": None, "단가(원)": 1900, "금액(원)": None, "비고": ""},
    {"번호": 12, "품명": "안전망1cm KS망", "규격": "가공품", "단위": "m2", "수량": None, "단가(원)": 2150, "금액(원)": None, "비고": ""},
    {"번호": 13, "품명": "멀티망", "규격": "1200D", "단위": "m2", "수량": None, "단가(원)": 420, "금액(원)": None, "비고": ""},
    {"번호": 14, "품명": "럿셀망", "규격": "1.2", "단위": "R/L", "수량": None, "단가(원)": 16000, "금액(원)": None, "비고": ""},
    {"번호": 15, "품명": "럿셀망", "규격": "1.5", "단위": "R/L", "수량": None, "단가(원)": 20000, "금액(원)": None, "비고": ""},
    {"번호": 16, "품명": "럿셀망", "규격": "1.8", "단위": "R/L", "수량": None, "단가(원)": 25000, "금액(원)": None, "비고": ""},
    {"번호": 17, "품명": "pp로프(400m)", "규격": "5mm", "단위": "R/L", "수량": None, "단가(원)": 14500, "금액(원)": None, "비고": ""},
    {"번호": 18, "품명": "pp로프(200m)", "규격": "6mm", "단위": "R/L", "수량": None, "단가(원)": 12000, "금액(원)": None, "비고": ""},
    {"번호": 19, "품명": "pp로프(200m)", "규격": "8mm", "단위": "R/L", "수량": None, "단가(원)": 20000, "금액(원)": None, "비고": ""},
    {"번호": 20, "품명": "pp로프(200m)", "규격": "10mm", "단위": "R/L", "수량": None, "단가(원)": 30000, "금액(원)": None, "비고": ""},
    {"번호": 21, "품명": "pp로프(200m)", "규격": "12mm", "단위": "R/L", "수량": None, "단가(원)": 43000, "금액(원)": None, "비고": ""},
    {"번호": 22, "품명": "pp로프(200m)", "규격": "16mm", "단위": "R/L", "수량": None, "단가(원)": 75000, "금액(원)": None, "비고": ""},
    {"번호": 23, "품명": "와이어로프", "규격": "", "단위": "M", "수량": None, "단가(원)": 330, "금액(원)": None, "비고": ""},
    {"번호": 24, "품명": "와이어클립", "규격": "", "단위": "EA", "수량": None, "단가(원)": 130, "금액(원)": None, "비고": ""},
    {"번호": 25, "품명": "케이블타이", "규격": "270mm", "단위": "봉", "수량": None, "단가(원)": 15000, "금액(원)": None, "비고": ""}
]

def load_initial_data():
    df = pd.DataFrame(DEFAULT_PRICES)
    df['기본단가'] = df['단가(원)'] # 숨김 처리용
    return df

def apply_discount():
    rate = st.session_state.quote_discount
    df = st.session_state.quote_df
    for idx in df.index:
        base_p = df.loc[idx, '기본단가']
        if pd.notna(base_p):
            df.loc[idx, '단가(원)'] = int(float(base_p) * (1 + rate / 100))

# 메인 UI
st.title("📄 견적서 작성 및 출력")

# ---------------------------------------------------------
# 견적서 기본 정보 입력란
# ---------------------------------------------------------
st.subheader("1. 견적서 기본 정보")
with st.expander("수신처 및 공급자 정보 입력 (클릭해서 열기)", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**[수신처 정보]**")
        q_date = st.date_input("견적일", datetime.date.today())
        q_name = st.text_input("견적명", "안전망, 로프 (단가견적)")
        q_recipient = st.text_input("수신처 (회사명)", value="", placeholder="예: 주식회사 경원안전")
        q_ref = st.text_input("참조", value="", placeholder="예: 한송이 차장")
        q_phone = st.text_input("수신처 전화/팩스", value="", placeholder="예: 전화 041-553-1021 / 팩스 041-553-1022")
    
    with col_b:
        st.markdown("**[공급자 정보 (석미세이프)]**")
        s_company = st.text_input("회사명", "석미세이프")
        s_address = st.text_area("주소", "경기도 남양주시 수동면 남가로 1771-1")
        s_biznum = st.text_input("사업자등록번호", "524-38-00469")
        s_contact = st.text_input("공급자 연락처", "Tel: 02-495-4584 / Fax: 02-495-4856")
        s_email = st.text_input("이메일", "sm_safe@naver.com")

st.divider()

# ---------------------------------------------------------
# 품목 및 단가 조정
# ---------------------------------------------------------
st.subheader("2. 품목 및 단가 입력")

# 초기 세팅
if 'quote_df' not in st.session_state: st.session_state.quote_df = load_initial_data()
if 'quote_discount' not in st.session_state: st.session_state.quote_discount = 0

# 단가 일괄 조정 너비 축소 (오류 해결 위해 value 제거)
col_adj1, col_adj2 = st.columns([1.5, 8.5])
with col_adj1:
    st.number_input("단가 일괄 조정 (%)", min_value=-100, max_value=100, step=5, key="quote_discount", on_change=apply_discount)

# --- 중간 행 삽입 기능 추가 ---
col_ins1, col_ins2, col_ins3 = st.columns([1.5, 2, 6])
with col_ins1:
    ins_idx = st.number_input("추가할 행 번호", min_value=1, max_value=len(st.session_state.quote_df)+1, value=1, step=1)
with col_ins2:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ 해당 번호에 행 삽입"):
        df = st.session_state.quote_df
        idx = int(ins_idx) - 1
        new_row = pd.DataFrame([{"번호": 0, "품명": "", "규격": "", "단위": "", "수량": None, "단가(원)": None, "금액(원)": None, "비고": "", "기본단가": None}])
        st.session_state.quote_df = pd.concat([df.iloc[:idx], new_row, df.iloc[idx:]]).reset_index(drop=True)
        st.session_state.quote_df['번호'] = range(1, len(st.session_state.quote_df) + 1)
        st.rerun()

st.caption("💡 **수량**을 입력하면 금액이 자동 계산됩니다. 빈 행을 클릭해 품목을 추가할 수 있습니다.")

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

# 실시간 금액 계산 로직
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
        elif len(nums) == 1 and re.search(r'[xX*]', spec): multiplier = nums[0]
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

# 기본단가 동기화
for idx in edited_df.index:
    try:
        if idx in st.session_state.quote_df.index:
            if st.session_state.quote_df.loc[idx, '단가(원)'] != edited_df.loc[idx, '단가(원)']:
                edited_df.loc[idx, '기본단가'] = edited_df.loc[idx, '단가(원)']
                changed = True
    except: pass

if changed or not edited_df.equals(st.session_state.quote_df):
    edited_df['번호'] = range(1, len(edited_df) + 1) # 행 추가/삭제 시 번호 자동 재정렬
    st.session_state.quote_df = edited_df.copy()
    st.rerun()

total_sum = edited_df['금액(원)'].dropna().sum()
st.markdown(f"<h4 style='text-align: right; color:#d32f2f;'>계산된 합계금액 : {int(total_sum):,} 원</h4>", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------
# 세련된 인쇄용(PDF) HTML 렌더링
# ---------------------------------------------------------
st.subheader("3. 견적서 출력 (미리보기)")
st.info("💡 아래 [📥 PDF 다운로드] 버튼을 누르면 PC와 모바일 모두에서 파일로 즉시 저장됩니다.")

# HTML 테이블 생성
tbody_html = ""
valid_rows = edited_df.dropna(subset=['품명']) # 품명이 있는 행만 출력
for i, row in valid_rows.iterrows():
    r_no = row.get('번호', '') if pd.notna(row.get('번호')) else ''
    r_item = row.get('품명', '') if pd.notna(row.get('품명')) else ''
    r_spec = row.get('규격', '') if pd.notna(row.get('규격')) else ''
    r_unit = row.get('단위', '') if pd.notna(row.get('단위')) else ''
    r_qty = f"{float(row['수량']):g}" if pd.notna(row.get('수량')) and str(row.get('수량')).strip() else ""
    r_price = f"{int(row['단가(원)']):,}" if pd.notna(row.get('단가(원)')) else ""
    r_amt = f"{int(row['금액(원)']):,}" if pd.notna(row.get('금액(원)')) else ""
    r_note = row.get('비고', '') if pd.notna(row.get('비고')) else ''
    
    tbody_html += f"""
    <tr>
        <td style='text-align:center; padding:3px 4px; border:1px solid #000;'>{r_no}</td>
        <td style='padding:3px 4px; border:1px solid #000;'>{r_item}</td>
        <td style='padding:3px 4px; border:1px solid #000;'>{r_spec}</td>
        <td style='text-align:center; padding:3px 4px; border:1px solid #000;'>{r_unit}</td>
        <td style='text-align:center; padding:3px 4px; border:1px solid #000;'>{r_qty}</td>
        <td style='text-align:right; padding:3px 4px; border:1px solid #000;'>{r_price}</td>
        <td style='text-align:right; padding:3px 4px; border:1px solid #000;'>{r_amt}</td>
        <td style='padding:3px 4px; border:1px solid #000;'>{r_note}</td>
    </tr>
    """

addr_html = s_address.replace("\n", "<br>")

html_template = f"""
<!-- PDF 변환 라이브러리 추가 -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>

<div style="text-align: right; max-width: 840px; margin: 0 auto 10px auto;">
    <button onclick="downloadPDF()" style="padding: 10px 20px; background-color: #ff4b4b; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">
        📥 PDF 다운로드
    </button>
</div>

<div id="invoice-box" style="font-family: 'Malgun Gothic', sans-serif; max-width: 800px; margin: 0 auto; padding: 15px 15px 30px 15px; border: 2px solid #333; background: #fff; color: #000;">
    <h1 style="text-align: center; letter-spacing: 10px; margin-bottom: 0px;">견 적 서</h1>
    <p style="text-align: center; margin-top: 0; font-size: 13px; color: #555;">건설안전자재 (안전망, 갱폼수직보호망)</p>
    
    <div style="display: flex; justify-content: space-between; margin-top: 15px; font-size: 13px;">
        <div style="width: 45%;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 3px 0; border-bottom: 1px solid #000; font-weight: bold; width: 60px;">수신처</td>
                    <td style="padding: 3px 0; border-bottom: 1px solid #000;">{f"{q_recipient} 귀하" if q_recipient else ""}</td></tr>
                <tr><td style="padding: 3px 0; border-bottom: 1px solid #000; font-weight: bold;">참조</td>
                    <td style="padding: 3px 0; border-bottom: 1px solid #000;">{q_ref}</td></tr>
                <tr><td style="padding: 3px 0; border-bottom: 1px solid #000; font-weight: bold;">연락처</td>
                    <td style="padding: 3px 0; border-bottom: 1px solid #000;">{q_phone}</td></tr>
            </table>
            <div style="margin-top: 10px;">
                <p style="margin: 3px 0;"><strong>견적일 : </strong> {q_date.strftime('%Y년 %m월 %d일')}</p>
                <p style="margin: 3px 0;"><strong>견적명 : </strong> {q_name}</p>
                <p style="margin: 3px 0; font-size: 15px;"><strong>합계금액 : </strong> <span style="font-size: 16px; font-weight: bold;">₩ {int(total_sum):,}</span> (VAT 별도)</p>
            </div>
        </div>
        
        <div style="width: 45%;">
            <table style="width: 100%; border-collapse: collapse; border: 2px solid #000;">
                <tr>
                    <td rowspan="4" style="width: 20px; text-align: center; border-right: 1px solid #000; border-bottom: 1px solid #000; writing-mode: vertical-lr; font-weight: bold;">공급자</td>
                    <td style="width: 90px; padding: 3px; border-right: 1px solid #000; border-bottom: 1px solid #000;">사업자번호</td>
                    <td style="padding: 3px; border-bottom: 1px solid #000;">{s_biznum}</td>
                </tr>
                <tr>
                    <td style="padding: 3px; border-right: 1px solid #000; border-bottom: 1px solid #000;">상호</td>
                    <td style="padding: 3px; border-bottom: 1px solid #000;"><strong>{s_company}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 3px; border-right: 1px solid #000; border-bottom: 1px solid #000;">주소</td>
                    <td style="padding: 3px; border-bottom: 1px solid #000; font-size: 12px;">{addr_html}</td>
                </tr>
                <tr>
                    <td style="padding: 3px; border-right: 1px solid #000;">연락처</td>
                    <td style="padding: 3px; font-size: 12px;">{s_contact}<br>E-mail: {s_email}</td>
                </tr>
            </table>
        </div>
    </div>
    
    <div style="margin-top: 15px;">
        <p style="margin-bottom: 5px; font-weight: bold; font-size: 13px;">아래와 같이 견적합니다. (VAT 별도)</p>
        <div style="border: 2px solid #000; border-bottom: 3px solid #000;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 4px; border: 1px solid #000; border-top: none; border-left: none; width: 40px;">번호</th>
                        <th style="padding: 4px; border: 1px solid #000; border-top: none; width: 150px;">품명</th>
                        <th style="padding: 4px; border: 1px solid #000; border-top: none;">규격</th>
                        <th style="padding: 4px; border: 1px solid #000; border-top: none; width: 50px;">단위</th>
                        <th style="padding: 4px; border: 1px solid #000; border-top: none; width: 50px;">수량</th>
                        <th style="padding: 4px; border: 1px solid #000; border-top: none; width: 80px;">단가(원)</th>
                        <th style="padding: 4px; border: 1px solid #000; border-top: none; width: 90px;">금액(원)</th>
                        <th style="padding: 4px; border: 1px solid #000; border-top: none; border-right: none; width: 70px;">비고</th>
                    </tr>
                </thead>
                <tbody>
                    {tbody_html}
                </tbody>
            </table>
        </div>
    </div>
    <div style="height: 20px;"></div>
</div>

<script>
    function downloadPDF() {{
        var element = document.getElementById('invoice-box');
        var opt = {{
            margin:       3,
            filename:     '{q_name}_견적서.pdf',
            image:        {{ type: 'jpeg', quality: 0.98 }},
            html2canvas:  {{ scale: 2 }},
            jsPDF:        {{ unit: 'mm', format: 'a4', orientation: 'portrait' }}
        }};
        html2pdf().set(opt).from(element).save();
    }}
</script>
"""

st.components.v1.html(html_template, height=1100, scrolling=True)

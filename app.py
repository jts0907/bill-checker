import streamlit as st
import anthropic
import pdfplumber
import io
import time

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="국회 의안(법률안) 주요쟁점 리뷰",
    page_icon="⚖️",
    layout="wide",
)

# ── 시스템 프롬프트 ───────────────────────────────────────────
SYSTEM_PROMPT = """당신은 법제처 『법령 입안·심사 기준』(2026년판)에 정통한 법제 전문가입니다.
제출된 의원발의 법률안 전문을 읽고, 아래 4개 항목에 대해 주요쟁점 리뷰를 수행하십시오.

## 리뷰 원칙

- 이 리뷰는 추가적인 정밀 리뷰를 위한 사전 스크리닝 목적입니다.
- 정밀 리뷰 필요성이 있으면 적극적으로 언급하되, 단정적으로 문제있다는 판단은 삼가고 "리뷰 필요" 수준으로 표시하십시오.
- 법안 본문에 명시된 내용을 근거로 리뷰하고, 현재 프로그램 구성상 외부 법령 데이터베이스 검색은 불가하므로 타법 관련 사항은 한계를 명시하십시오.
- 각 리뷰 사항에는 반드시 해당 조문(조·항·호)을 특정하십시오.

---

## 리뷰 항목 1: 체계·형식

다음 각 사항을 순서대로 리뷰하십시오.

### 1-1. 조·항·호·목 구조
- 항(①②)이 완성된 문장 형식인지 확인 (미완성 어절로 끝나면 문제)
- 호(1. 2. 3.)가 "…한다"로 끝나는지 확인 → 원칙적으로 금지 (단서·후단 제외)
- 목(가. 나.)이 "…한다" 형식으로 끝나는지 확인 → 금지
- 하나의 항에 3개 이상 문장이 포함된 경우 → 전단·후단·단서 구분 검토 필요

### 1-2. 정의 규정
- 정의 규정 제목이 "(정의)"인지 확인
- 정의 내용에 "등", "그 밖에", "…와 같은" 등 불확정 표현 포함 여부
- 정의된 용어를 재약칭한 경우 → 원칙적으로 금지
- 하위법령에서 상위법령이 이미 정의한 동일 용어를 재정의한 경우 → 금지
- 정의 규정에 인허가 요건 등 실체적 내용 혼재 여부

### 1-3. 약칭 사용
- 자주 반복되지 않는 용어에 약칭 사용 여부
- 약칭만 보고 원래 의미를 유추하기 어려운 경우
- 법령 전반에 걸쳐 사용되는 기본 용어를 약칭 처리한 경우 (정의 조항 사용이 원칙)

### 1-4. 장·절 구성
- 본칙 조문이 30개 이상임에도 장 구분 없는 경우
- 부칙에 장·절 구분이 있는 경우 → 금지
- 총칙과 통칙 혼용 여부

### 1-5. 부칙
- 시행일 규정 존재 여부
- 경과조치 필요 여부 검토 (기존 법률관계 영향 조항 존재 시)
- 기존 법령의 개정·폐지 사항이 부칙에 적절히 반영되었는지

### 1-6. 법령 인용 방식
- 타 법령 인용 시 정식 법령명 사용 여부
- "제○조에 따른"과 "제○조의"의 구분 적정성

---

## 리뷰 항목 2: 위임입법 관련

### 2-1. 위임 근거 확인
하위법령(대통령령·총리령·부령·고시 등)으로 위임하는 조항이 있는 경우:
- 위임 형식의 적정성 판단
  · 국민의 권리·의무에 관한 실체적 사항 → 대통령령 위임이 원칙
  · 절차·서식 등 집행적 사항 → 총리령·부령 가능
  · 고시 등 행정규칙 위임 → 전문적·기술적으로 불가피한 예외적 경우에만 허용

### 2-2. 포괄위임 해당 가능성
각 위임 조항에 대해:
- 위임받는 법령에 규정될 내용의 대강을 법률 본문에서 예측할 수 있는지
- "필요한 사항은 대통령령으로 정한다"만 있는 경우 → 포괄위임 우려, 구체적으로 언급
- 처벌 법규·조세 법규에 대한 위임 → 구체성·명확성 요건 강화

### 2-3. 위임 범위 준수 (법률안의 경우 해당사항 없음, 대통령령 등 하위법령 개정·신설의 경우에 한정해서 적용)
대법원 판단기준 5가지 적용 리뷰:
① 의회유보 원칙이 지켜져야 할 본질적 사항을 하위법령에서 규정하는지
② 해당 법률의 입법 목적·규정 체계·다른 규정과의 관계를 종합 고려했는지
③ 위임 규정의 문언적 의미 한계를 벗어나는지
④ 모법으로부터 위임 내용의 대강을 예측할 수 있는 범위인지
⑤ 용어 의미를 넘어 범위를 확장·축소하여 새로운 입법을 한 것으로 볼 수 있는지

### 2-4. 재위임 여부
하위법령이 다시 더 하위의 법령으로 재위임하는 경우 → 원래 위임 취지 범위 내인지

---

## 리뷰 항목 3: 타법 저촉·중복 가능성 

⚠️ **한계 고지**: 시스템의 제약이나 법령정보 검색이 불가능하므로 다음과 같은 한계 고지를 해야 함. " 법안 본문에 명시된 정보만으로 리뷰함에 따라 전체 데이터베이스 접근이 불가한 쟁점은 확인 불가 사항으로 명시합니다."

### 3-1. 법안 내 타법 관계 조항 분석
- 타법과의 관계를 명시한 조항 존재 여부
- 특별법-일반법 관계가 명확히 설정되어 있는지
- 준용 조항의 적정성 (준용 범위, 규율 대상의 유사성)

### 3-2. 동일 사항 중복 규율 가능성
- 법안 본문에서 인용·언급된 타법명을 기초로 중복 가능성 언급
- 특별법 제정의 필요성이 법안 내에서 충분히 설명되고 있는지

### 3-3. 개정 조항의 정합성
기존 법령 조항을 개정하는 부칙 조항이 있는 경우:
- 개정 형식의 적정성
- 관련성 있는 법령을 함께 개정하고 있는지 여부 (누락 가능성 언급)

---
## 리뷰 항목 4: 의원입법 주요 모니터링 사항

### 4-1. 법안 내 예산 관련 조항 존재 여부 분석
- 국가나 지방자치단체의 예산 지원, 예비타당성 검토 예외 인정하는 조항 존재 여부
- 국가나 지방자치단체의 의무적 예산지원 규정이 존재하는 경우는 반드시 체크해서 중요사항으로 명시

### 4-2. 법안 내 행정 조직 관련 조항 여부 분석
- 법안 본문에서 중앙행정기관이나 위원회를 신설하거나 확대설치하는 조항 존재 여부
- 법안과 특별법 관계에 있는 현행 법률에서 위원회나 행정조직을 규정하고 있는 경우, 개정안에서 규정하는 위원회 등 조직이 해당 위원회와의 중복여부 체크

### 4-3. 규제 강화 여부 분석
- 법안 본문에서 국민의 권리를 제한하거나 의무를 부과하는 규제를 신설하거나 강화하는 조항이 존재하는지 
- 해당 개정사항이 행정규제기본법과 상충되는 내용은 아닌지

### 4-4. 지방자치제도 강화 제약 여부 분석
- 법안 본문에서 하위법령으로 위임하는 사항 중 각 지방자치단체별 고유한 규율이 가능한 사항(지방자치법상 자치사무)에 해당할 가능성이 있는지  
- 해당 개정사항을 하위법령이 아닌 지방자치단체의 조례로 위임하는 방안을 고려할 필요성(해당 현행 법률상 유사한 사항에 대해 조례로 위임하고 있는지) 

### 4-5. 형벌규정 관련
- 법안 본문에서 형사처벌 규정을 신설하거나 기존 처벌 대상을 확대, 처벌 수준을 상향 변경 하는 규정이 있는지  
- 각 규정의 주요 내용(구성요건 신설, 법정형, 형벌의 감면 등)을 정리하고, 형사처벌규정 소관부처(법무부) 협의 필요함을 명시 

---
## 리뷰 항목 5: 헌법 측면

### 5-1. 기본권 제한 조항 존재 여부 확인
법안에서 국민의 자유·권리를 제한하거나 의무를 부과하는 조항을 모두 식별하고 해당 조문을 명시하십시오.

### 5-2. 법률유보 원칙
- 기본권 제한이 법률 조항으로 규정되는지, 또는 하위법령에 위임되는지
- 기본권 제한의 핵심 사항을 하위법령에 위임 → 의회유보 저촉 가능성 확인

### 5-3. 비례원칙(과잉금지원칙) — 헌법 제37조 제2항
기본권 제한 조항에 대해 4단계 검토:

**① 목적의 정당성**
- 입법 목적이 국가안전보장·질서유지·공공복리에 해당하는지

**② 방법의 적정성**
- 선택한 수단이 입법 목적 달성에 효과적·적절한지
- 목적과 수단 간의 합리적 연관성

**③ 피해의 최소성** ← 위헌 결정에서 가장 자주 문제되는 항목
- 덜 침해적인 대안 수단이 존재하는지
- 일률적·획일적 제한 규정 여부 (예외·완화 조항 부재)
- 제재 규정 시 위반 경중에 따른 차등 없는 일률 규정 여부

**④ 법익의 균형성**
- 보호하려는 공익과 침해되는 사익 간 균형 여부
- 기본권의 본질적 내용을 침해하는 수준인지

### 5-4. 명확성 원칙
- 침익적 규정·형사법·조세법 조항의 불확정 개념 사용 여부
- 불확정 개념 사용 시 용어 정의·한정 수식어·적용 한계 조항으로 보완되었는지
- 행정기관에 과도한 재량을 부여하는 요건 설정 여부

### 5-5. 평등 원칙
- 특정 집단·대상에 대한 차별적 취급 조항 여부
- 차별이 있는 경우 합리적 근거와 목적과의 실질적 관련성

### 5-6. 소급입법 여부
- 이미 완성된 사실관계·법률관계에 새로운 의무 부과 또는 불이익 부과 여부
- 부칙의 적용례·경과조치 조항의 소급 적용 가능성

### 5-7. 적법절차 원칙
- 불이익 처분·제재 규정에서 당사자 고지·의견제출 기회 부여 조항 존재 여부
- 청문 규정의 필요성 여부 (면허·허가 취소 등 중요한 권익 침해 시)

---

## 출력 형식

### 법안 개요
- 법안명:
- 개정/제정 형식:
- 주요 규율 내용 (3줄 이내):

---

### 리뷰 결과

각 항목별로 다음 형식으로 출력하십시오.

**[항목명]**
- 결과: 🟢 이상 없음 / 🟡 리뷰 필요 / 🔴 정밀 리뷰 필요
- 리뷰 요약 사항:
  - (조문 특정) 제○조제○항: [구체적 문제 내용 및 근거]
- 해당 사항 없음인 경우: "이 법안에서 해당 사항 없음"으로 표시

---

### 종합 의견
- 주요 쟁점 요약 (3~5개)
- 담당자 우선 리뷰 권고 사항"""


USER_PROMPT_TEMPLATE = """아래 법률안에 대해 주요쟁점 리뷰를 수행하십시오.

[법률안 전문]
{bill_text}"""


# ── PDF 텍스트 추출 ───────────────────────────────────────────
def extract_text_from_pdf(uploaded_file) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


# ── Claude API 호출 (프롬프트 캐싱 적용) ─────────────────────
def run_review(api_key: str, bill_text: str) -> tuple[str, dict]:
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # 시스템 프롬프트 캐싱
            }
        ],
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(bill_text=bill_text),
            }
        ],
    )

    result_text = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(
            response.usage, "cache_creation_input_tokens", 0
        ),
        "cache_read_input_tokens": getattr(
            response.usage, "cache_read_input_tokens", 0
        ),
    }
    return result_text, usage


# ── 비용 계산 ─────────────────────────────────────────────────
def calc_cost(usage: dict) -> float:
    input_cost = usage["input_tokens"] * 3.0 / 1_000_000
    output_cost = usage["output_tokens"] * 15.0 / 1_000_000
    cache_write_cost = usage["cache_creation_input_tokens"] * 3.75 / 1_000_000
    cache_read_cost = usage["cache_read_input_tokens"] * 0.30 / 1_000_000
    return input_cost + output_cost + cache_write_cost + cache_read_cost


# ── session_state 초기화 ──────────────────────────────────────
if "review_history" not in st.session_state:
    st.session_state.review_history = []

# ── UI ────────────────────────────────────────────────────────
st.title("⚖️ 국회 의안(법률안) 주요쟁점 리뷰 시스템")
st.caption("법령 입안·심사 기준(2026)에 근거한 AI 기반 법률안 주요쟁점 사전 리뷰(스크리닝) 도구")

# 사이드바 — API 키 설정
with st.sidebar:
    st.header("⚙️ 설정")

    # secrets에 키가 있으면 자동 로드, 없으면 입력 받기
    if "anthropic_api_key" in st.secrets:
        api_key = st.secrets["anthropic_api_key"]
        st.success("API 키가 설정되어 있습니다.")
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="platform.anthropic.com에서 발급",
        )

    st.divider()
    st.markdown("""
**리뷰 항목**
1. 체계·형식
2. 위임입법 관련
3. 타법 저촉·중복 우려
4. 의원입법 주요 모니터링 사항
5. 헌법 측면

**사용 모델**  
Claude Sonnet 4.6  

**참고 기준**  
법제처 법령 입안·심사 기준 (2026년판)
""")

# 메인 영역
st.subheader("📄 법안 입력")

st.markdown("""
<style>
[data-testid="stFileUploader"] {
    width: fit-content;
    min-width: 400px;
}
</style>
""", unsafe_allow_html=True)

input_method = st.radio(
    "입력 방식 선택",
    ["PDF 업로드", "텍스트 직접 입력"],
    horizontal=True,
)

bill_text = ""
uploaded_file = None

if input_method == "PDF 업로드":
    uploaded_file = st.file_uploader(
        "법안 PDF 파일을 업로드하세요",
        type=["pdf"],
        help="국회 의안정보시스템에서 다운로드한 PDF",
    )
    if uploaded_file:
        with st.spinner("PDF에서 텍스트 추출 중..."):
            try:
                bill_text = extract_text_from_pdf(uploaded_file)
                st.success(f"텍스트 추출 완료 ({len(bill_text):,}자)")
            except Exception as e:
                st.error(f"PDF 추출 오류: {e}")
else:
    st.markdown("""
<style>
[data-testid="stTextArea"] textarea {
    width: 600px;
}
</style>
""", unsafe_allow_html=True)
    bill_text = st.text_area(
        "법안 전문을 붙여넣으세요",
        height=300,
        placeholder="제안이유, 조문 내용, 부칙 등 전체 텍스트를 붙여넣으세요.",
    )
# 리뷰 실행
st.divider()

col1, col2 = st.columns([1, 4])
with col1:
    run_button = st.button(
        "🔍 리뷰 시작",
        type="primary",
        disabled=not (api_key and bill_text),
        use_container_width=True,
    )

if not api_key:
    st.warning("사이드바에서 Anthropic API Key를 입력해 주세요.")

if run_button and api_key and bill_text:
    st.subheader("📋 리뷰 결과")

    with st.spinner("AI가 리뷰 중... (약 20~40초 소요)"):
        try:
            start_time = time.time()
            result, usage = run_review(api_key, bill_text)
            elapsed = time.time() - start_time
            cost = calc_cost(usage)
            
            # ── 결과 session_state에 저장 (최대 3건) ──────────
            import re
            title_match = re.search(r"법안명[:\s*]*(.+)", result)
            bill_title = title_match.group(1).strip() if title_match else f"검토 {len(st.session_state.review_history)+1}건"
            st.session_state.review_history.insert(0, {
                "title": bill_title[:30],
                "result": result,
                "usage": usage,
                "cost": cost,
                "elapsed": elapsed,
            })
            if len(st.session_state.review_history) > 3:
                st.session_state.review_history = st.session_state.review_history[:3]

            

        except anthropic.AuthenticationError:
            st.error("API 키가 유효하지 않습니다. 키를 확인해 주세요.")
        except anthropic.RateLimitError:
            st.error("API 요청 한도 초과입니다. 잠시 후 다시 시도해 주세요.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
# ── 검토 결과 이력 표시 ───────────────────────────────────────
if st.session_state.review_history:
    st.subheader("📋 리뷰 결과")
    tabs = st.tabs([f"{'🕐' if i==0 else '🕑' if i==1 else '🕒'} {r['title']}"
                    for i, r in enumerate(st.session_state.review_history)])
    for tab, record in zip(tabs, st.session_state.review_history):
        with tab:
            st.markdown(record["result"])
            st.divider()
            with st.expander("📊 토큰 사용량 및 비용"):
                cols = st.columns(4)
                cols[0].metric("입력 토큰", f"{record['usage']['input_tokens']:,}")
                cols[1].metric("출력 토큰", f"{record['usage']['output_tokens']:,}")
                cols[2].metric("소요 시간", f"{record['elapsed']:.1f}초")
                cols[3].metric("추정 비용", f"${record['cost']:.4f}")
            st.download_button(
                label="📥 리뷰 결과 다운로드 (.txt)",
                data=record["result"],
                file_name=f"주요리뷰결과_{record['title']}.txt",
                mime="text/plain",
                key=f"download_{id(record)}",
            )

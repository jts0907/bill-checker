# 국회 의안(법률안) 주요 쟁점 리뷰 시스템

스트림리트 앱 시안 링크 [https://bill-checker-vtwkx8kmjyxvax3fzctef3.streamlit.app/](https://bill-checker-claude4602.streamlit.app/)

법령 입안·심사 기준(2026)에 근거한 AI 기반 의원발의안 사전 리뷰(스크리닝) 도구.

## 리뷰 항목

1. **체계·형식** — 조·항·호·목 구조, 정의 규정, 약칭, 장·절 구성, 부칙, 법령 인용
2. **위임입법 관련** — 위임 근거, 포괄위임 여부, 위임 범위, 재위임
3. **타법 저촉·중복 가능성** — 타법 관계 조항, 중복 규율, 개정 조항 정합성
4. **의원입법 주요 모니터링 사항** - 예산, 조직, 규제, 지방자치, 형벌 규정 존재 여부 모니터링
5. **헌법 측면** — 법률유보, 비례원칙(4단계), 명확성, 평등, 소급입법, 적법절차

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

API 키는 `.streamlit/secrets.toml`에 입력하거나 앱 사이드바에서 직접 입력.

## Streamlit Cloud 배포

1. 이 저장소를 GitHub에 push
2. [share.streamlit.io](https://share.streamlit.io) 접속 → New app
3. 저장소 선택 → Main file: `app.py`
4. **App settings > Secrets** 에 아래 입력:
   ```
   anthropic_api_key = "sk-ant-..."
   ```
5. Deploy 클릭

> ⚠️ `.gitignore`에 `secrets.toml`이 포함되어 있으므로 API 키가 GitHub에 노출되지 않습니다.

## 파일 구조

```
├── app.py                  # 메인 앱
├── requirements.txt        # 의존성
├── .gitignore
├── .streamlit/
│   └── secrets.toml        # API 키 (git 제외)
└── README.md
```

## 사용 모델

- Claude Sonnet 4.6 (`claude-sonnet-4-6`)
- 시스템 프롬프트 캐싱 적용 (반복 검토 시 비용 절감)
- 건당 예상 비용: 약 $0.02~0.03

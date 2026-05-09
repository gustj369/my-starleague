# 진행 상태 (plan.md)

_최종 업데이트: 2026-05-09 (v1.0.0 출시)_

## 완료된 작업 ✅

### 핵심 기능
- [x] 16강 토너먼트 브라켓 + AI 자동 시뮬레이션
- [x] 3페이즈 세트 시뮬레이션 (초반/중반/후반)
- [x] 전술 삼각 시스템 (공세/수비/기동)
- [x] 등급별 언더독 부스트 + 강자 패널티
- [x] 다전제 역전 모멘텀 (gap×4, 최대 +8)
- [x] 선수 성장 시스템 (경기 델타 + 토너먼트 성장 이벤트)
- [x] 피로도 시스템 + 컨디션 시스템
- [x] 아이템 상점 (능력치/컨디션/피로회복)
- [x] 라이벌 시스템 (특별 변동성 확장)
- [x] 5슬롯 세이브/로드
- [x] 도전과제 / 업적 시스템 (11종, earn_achievement + check_and_earn_achievements)

### IP 제거 (스타크래프트 → 오리지널)
- [x] 종족: 테란/저그/프로토스 → 질풍파/홍염파/철벽파 (DB값 유지, UI만 변환)
- [x] 전술: 가위/바위/보 + 종족빌드 → 공세/수비/기동 삼각체계
- [x] 맵: SC 맵명 → 오리지널 맵명 (번개 평원, 습지 요새 등 10개)
- [x] 선수: 오리지널 이름 16명 (나이엘, 루엔, 벨리아 등)

### 기술적 수정
- [x] EXE 새 게임 클릭 시 즉시 종료 버그 수정 (parents=True, frozen 분기)
- [x] 내비게이션 돌아가기 버그 수정 (_NAV_SCREENS frozenset)
- [x] 선수 이미지 EXE 번들 (sys._MEIPASS 분기)
- [x] Super 등급 도입 (SSS → Super 전체 변경 + DB 마이그레이션)
- [x] 선수 아바타 (파벌 심볼+컬러), 점수 도트, 이변 배너 추가

### 밸런스 패치 (2026-04-17)
- [x] 고OVR 성장 감쇄 — Super max+1 / SS max+2 / S max+cfg-1 (match & tournament 양쪽)
- [x] 맵 보너스 축소 — 최대 +5/-3, 최대 스윙 8pt + 기존 DB 마이그레이션 SQL
- [x] 아이템 가격 재조정 — 컨트롤·공격력 190G, 수비력·전략·물량·센스 130G
- [x] 전략 상성 — 후반체력전 중반 버팀 +3 / 후반 +14, AI에도 전략_b 적용
- [x] 전략 라벨 수정 (+12/-6 실제값 반영) + 세트 결과에 AI 전략 공개 뱃지

### QA 버그픽스 (2026-04-18)
- [x] BUG-06 [CRITICAL] seed_data: DELETE→UPSERT (player_items cascade 삭제 방지)
- [x] BUG-11 match: simulate_set() try/finally 커넥션 누수 방지
- [x] BUG-13 match: _apply_loser_delta() sense 이중 감소 수정 (extra_key 풀에서 sense 제외)
- [x] BUG-10 match_prep: AI Super/SS 상대에게도 최악 맵 핸디캡 적용
- [x] BUG-03 match_prep: 라이벌 UI 문구 정정 (능력치→운 변동성 보너스)
- [x] BUG-07 shop_screen: _buy_item() 단일 트랜잭션 원자화
- [x] BUG-08 simulation_screen: applied 플래그로 무효 아이템 삭제 방지
- [x] BUG-04 balance: map_bonus를 fatigue/condition 배수 밖으로 이동
- [x] BUG-01 builds: 유효하지 않은 전술 입력 → 중립(0) 처리
- [x] BUG-12 db: _ACTIVE_SLOT=-1 기본값 접근 시 RuntimeError 가드
- [x] BUG-14 db: add_gold() SQL UPDATE로 원자화

### QA 2차 패치 (2026-04-18)
- [x] QA-TIE match: 3페이즈 동점 시 random.choice() 랜덤 처리 (기존 >= 연산자 → 편향 제거)
- [x] QA-DRINK match_prep: 음료 사용 후 잔여 아이템 재확인 + 버튼 상태 즉시 갱신
- [x] QA-GUARD-START match_prep: 대결 시작 버튼 연타 방지 (클릭 즉시 비활성화)
- [x] QA-GUARD-FIN simulation_screen: _finalize() 재진입 방지 플래그 (_match_over 즉시 해제)
- [x] QA-WAL db: WAL 저널 모드 활성화 (강제 종료 시 DB 정합성 보장)
- [x] QA-SHOP-BTN shop_screen: 구매 버튼 try/finally 연타 방지

### 배포 전 품질 향상 + v1.0.0 출시 (2026-05-09)
- [x] P1 버그: 경기 화면 중복 입력 방지 (_set_running 플래그, 3중 가드)
- [x] 설정 화면 추가 (중계 속도 4단계, 수동 확인 체크리스트 링크)
- [x] 도전과제 화면 추가 (11종 업적 표시, 달성 시 초록 테두리)
- [x] AI 개성 시스템 (ai_style: 공격형/수비형/균형형, 전략 가중치 영향)
- [x] 스킵 버튼 (경기 중 즉시 결과 확인)
- [x] 중계 속도 설정 DB 저장 및 simulation_screen 실시간 반영
- [x] 스폰서 미션 시스템 (토너먼트마다 랜덤 미션, 골드 보상)
- [x] 전역 예외 핸들러 + error.log 파일 기록 (EXE/개발 양쪽)
- [x] NavBar 골드 표시 한국어 통일: 💰 N,NNN G (천 단위 쉼표)
- [x] NavBar 활성 버튼 하이라이트 (현재 서브화면 버튼 강조)
- [x] 윈도우 타이틀 화면 이름 반영 (화면 전환마다 갱신)
- [x] 설정 화면 하단 버전 정보 표시 (앱 버전 | DB 버전)
- [x] build.bat 빌드 스크립트 추가
- [x] APP_VERSION 중복 제거 (main.py 단일 정의 → splash_screen 파라미터 전달)
- [x] requirements.txt 버전 == 고정 (PyQt6 6.11.0, sip 13.11.1, pyinstaller 6.19.0)
- [x] verify_project_rules.py: requirements == 고정 검사 추가
- [x] .gitignore 강화 (.env* 차단 + .env.example 허용)
- [x] .env.example 템플릿 추가 + 보안 규칙 문서화
- [x] 설정 화면 문서 링크 클릭 가능 (GitHub URL)
- [x] manual-checklist.md 수동 확인 체크리스트 작성

---

## 현재 버전
- **EXE**: `dist/LegendLeague.exe` (2026-05-09 v1.0.0 출시 빌드)
- **DB 버전**: 6

---

## 다음 고려 사항 🔜
- [ ] 시즌 모드 (여러 토너먼트 연속 진행)
- [ ] 더 많은 아이템 / 희귀 이벤트
- [ ] 선수 영입/방출 시스템

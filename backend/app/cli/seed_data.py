"""Fictional seed content: 2 centers, 4 mentors, 12 children, 60 records.

All names are invented aliases. No real child information is ever used in
development or demos. Dates are offsets in days from "today" (Korea time)
so the demo always shows active, ended and upcoming assignments. The one
exception is the story child (see STORY_ANCHOR).
"""

from __future__ import annotations

from datetime import date

# (did, stuck, next_step) — the last four match the handover card example in the plan.
STARLIGHT_SESSIONS = [
    ("정수와 유리수 복습", "음수 곱셈 부호", "유리수 사칙연산"),
    ("유리수 사칙연산", "분수 나눗셈 순서", "혼합 계산 연습"),
    ("혼합 계산 연습", "괄호 계산 순서", "문자 사용"),
    ("문자 사용과 식의 값", "대입할 때 괄호 빠뜨림", "일차식 계산"),
    ("일차식의 덧셈과 뺄셈", "동류항 구분", "일차식 곱셈"),
    ("일차식과 수의 곱셈", "분배법칙 적용", "등식의 성질"),
    ("등식의 성질", "양변에 같은 수 나누기", "방정식 뜻"),
    ("방정식과 항등식 구분", "항등식 판별", "진단 문제"),
    ("시험 대비 복습", "서술형 풀이 쓰기", "진단 문제"),
    ("진단 문제", "분수 계산이 느림", "문자와 식 복습"),
    ("문자와 식 복습", "괄호 앞 음수의 분배", "방정식 풀이"),
    ("일차방정식 풀이", "이항할 때 부호 실수", "활용 문제 시작"),
    ("일차방정식 활용 3문제", "거리·속력 문제에서 식 세우기", "조건을 표로 정리하는 연습"),
]
SUCCESSOR_SESSIONS = [
    ("조건을 표로 정리하는 연습", "표에서 식으로 옮기기", "거리·속력 활용 2문제"),
    ("거리·속력 활용 2문제", "단위 맞추기", "농도 문제 맛보기"),
]
GENERIC_SESSIONS = [
    ("영어 단어 20개 복습", "철자 헷갈림", "단어 시험"),
    ("국어 비문학 지문 읽기", "중심 문장 찾기", "요약 연습"),
    ("구구단 7단·8단", "8단 뒷부분", "곱셈 문장제"),
    ("받아올림 있는 덧셈", "자리 맞추기", "뺄셈 시작"),
    ("과학 물질의 상태", "용어 구분", "실험 보고서 읽기"),
    ("영어 문장 만들기", "be동사와 일반동사", "의문문 만들기"),
    ("분수의 덧셈", "통분", "분수의 뺄셈"),
    ("일기 쓰기", "문단 나누기", "띄어쓰기 점검"),
]
SHARE_TEXTS = {
    "별빛": ["간식 제공 전 담당자 확인", "긴 문제는 소리 내어 읽게 하면 집중이 잘 됨"],
    "하늘": ["숙제는 센터에서 끝내고 가는 것을 좋아함"],
    "해님": ["처음 만나는 선생님에게 낯을 가리니 천천히 다가가기"],
}
NOTE_BODIES = {"별빛": "우유 알레르기 있음. 간식은 담당자가 직접 확인."}

# The 별빛 handover is the story on the poster and in the demo video, so its two
# assignments are laid out from this fixed day instead of today: 김하람 07.03 ~ 09.29,
# 이도윤 09.30 ~ 12.20 (offsets -100/-12 and -11/70 below). The seeder falls back to
# today whenever that timeline would no longer read correctly (``story_base``).
STORY_CHILD = "별빛"
STORY_ANCHOR = date(2026, 10, 11)

# Assignment plan: (child alias, mentor login id, start offset, end offset).
CENTERS = [
    {
        "name": "햇살지역아동센터",
        "prefix": "sunny",
        "mentors": [("mentor_kim", "김하람"), ("mentor_lee", "이도윤")],
        "children": [
            ("별빛", "중2"),
            ("하늘", "초5"),
            ("바다", "초3"),
            ("구름", "중1"),
            ("나무", "초6"),
            ("새봄", "고1"),
        ],
        "sensitive_basis": {"별빛", "하늘"},
        "assignments": [
            ("별빛", "mentor_kim", -100, -12),
            ("별빛", "mentor_lee", -11, 70),
            ("하늘", "mentor_kim", -40, 60),
            ("바다", "mentor_kim", -40, 60),
            ("구름", "mentor_lee", -35, 60),
            ("나무", "mentor_lee", -35, 60),
            ("새봄", "mentor_lee", 3, 90),
        ],
    },
    {
        "name": "달빛지역아동센터",
        "prefix": "moon",
        "mentors": [("mentor_park", "박서연"), ("mentor_choi", "최지후")],
        "children": [
            ("해님", "초4"),
            ("별님", "중3"),
            ("들꽃", "초2"),
            ("바람", "중1"),
            ("은하", "초6"),
            ("솔잎", "고2"),
        ],
        "sensitive_basis": {"해님"},
        "assignments": [
            ("해님", "mentor_park", -45, 60),
            ("별님", "mentor_park", -45, 60),
            ("들꽃", "mentor_park", -45, 60),
            ("바람", "mentor_choi", -60, -5),
            ("은하", "mentor_choi", -60, -5),
            ("솔잎", "mentor_park", -30, 60),
        ],
    },
]
GENERIC_RECORDS_PER_CHILD = 4
# One extra record for these children so the total is exactly 60 (15 + 9x4 + 5 + 4).
EXTRA_RECORD_CHILDREN = frozenset({"하늘", "바다", "구름", "나무", "해님"})

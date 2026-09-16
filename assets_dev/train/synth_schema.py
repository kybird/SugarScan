# 프로파일 값의 모양과 뜻 — 에디터가 위젯과 설명을 고르는 근거.
#
# 배경(2026-09-15): 에디터 1판이 모든 값을 자유 입력으로 냈고 설명이 없었다.
# 사람 지적: "right 이런 값은 고르게 해야지", "항목들이 뭘 의미하는지 알 수
# 없다". 열거값을 손으로 치게 두면 오타가 조용히 '옛 동작'으로 떨어진다 —
# time 의 pos="top-left" 가 렌더러에 분기가 없어 below 로 떨어진 사고가
# 실제로 있었다(같은 날).
#
# 이 표는 **렌더러가 실제로 분기하는 값**이다. synth_panel 의 분기를 읽고
# 적었고, 새 분기를 만들면 여기도 같이 고친다. 설명도 여기 둔다 — 값을
# 소비하는 코드 옆에 있어야 갈라지지 않는다.
#
# 항목 모양:
#   {"t": "num", "min":, "max":, "step":, "help":}   숫자(슬라이더+입력)
#   {"t": "enum", "opts": [...], "help":}            고르기
#   {"t": "enums", "opts": [...]}                    여러 개 고르기
#   {"t": "bool"}                                    켜고 끄기
#   {"t": "strs"}                                    문자열 목록
#   {"t": "str"}                                     자유 문자열(형식 문자열)
#   {"t": "nums", "n":, "labels":}                   고정 길이 숫자 목록
from synth_panel import LCD_ICONS

# 요소가 놓일 수 있는 자리 — 렌더러 분기 그대로.
UNIT_POS = ["below-right", "below", "above-right"]
TIME_POS = ["below-left", "below-right", "below-center", "row-bottom",
            "top-left", "top-right", "column"]
MEM_POS = ["top-left", "top-right", "below-left", "right-of-digits"]
ICON_POS = ["top-left", "top-right", "right-mid", "right-of-digits"]
BEZEL_EDGE = ["top", "bottom"]
ALIGN = ["right", "left", "center"]


def _n(mn, mx, st, help):
    return {"t": "num", "min": mn, "max": mx, "step": st, "help": help}


def _e(opts, help):
    return {"t": "enum", "opts": opts, "help": help}


P = _n(0.0, 1.0, 0.05,
       "이 요소가 뜰 확률. 기기 고정 프로파일은 대개 1.0 에 가깝다 — "
       "실물에 늘 있는 표시가 장마다 사라지면 다른 물건으로 보인다.")

REGIONS_SCHEMA = {
    "pad": {"t": "nums", "n": 4, "labels": ["좌", "우", "상", "하"],
            "min": 0.0, "max": 0.4, "step": 0.005,
            "help": "유리 안쪽 여백(유리 크기 대비). 실물 액정은 가장자리에 "
                    "구동 배선 띠가 있어 0 이 될 수 없다. 좌우를 줄이면 "
                    "숫자가 커진다 — 숫자는 남은 폭을 다 쓴다."},
    "rows": {"t": "nums", "n": 3, "labels": ["top", "mid(숫자)", "bottom"],
             "min": 0.0, "max": 1.0, "step": 0.005,
             "help": "안쪽 면을 위·가운데·아래로 나누는 비율(합이 1 이 아니어도 "
                     "정규화한다). 혈당 숫자는 mid 에 산다. 0 인 줄은 영역을 "
                     "만들지 않는다. mid 를 키워도 숫자가 안 커질 수 있다 — "
                     "폭에 먼저 걸리면 거기서 멈춘다."},
    "track_right": _n(0.0, 0.5, 0.005,
                      "오른쪽에 세로 트랙을 뗀다(미터기 점 눈금 열 자리). "
                      "그만큼 숫자 영역이 좁아진다."),
    "column_right": _n(0.0, 0.8, 0.005,
                       "가로형에서 오른쪽 정보 칼럼(시각·날짜·단위·M)이 "
                       "차지하는 폭."),
}

# 요소별 필드. 스키마에 없는 키는 형으로 추측해 자유 입력으로 떨어진다.
FIELDS = {
    "unit": {
        "texts": {"t": "strs",
                  "help": "단위 표기. 여러 개를 두면 기기 id 로 하나를 정해 "
                          "고른다 — 같은 기기가 장마다 다른 표기를 쓰면 "
                          "실물에 없는 변형을 가르친다."},
        "pos": _e(UNIT_POS,
                  "단위 자리. 값과 같은 줄에는 못 놓는다(렌더러가 assert 로 "
                  "막는다) — 근거 사진 9종 전부 숫자 아래다."),
        "hug": _n(0.0, 0.8, 0.01,
                  "단위가 숫자에 얼마나 바싹 붙는가. **숫자 아랫변**에서 잰 "
                  "간격(숫자 높이 대비). 0 이면 숫자에 닿고, 0.10 이 밴드 "
                  "경계다 — 그보다 작으면 밴드 안으로 들어간다(실물에 그런 "
                  "기기가 있다). 기기 속성이다."),
        "h": _n(0.3, 1.6, 0.02,
                "글자 높이 배수(1.0 = 시간·날짜 줄과 같은 크기). 1 보다 "
                "작으면 단위가 더 작아진다."),
        "gap": {"t": "nums", "n": 2, "min": 0, "max": 200, "step": 1,
                "help": "below-* 에서는 쓰이지 않는다(간격은 hug 가 정한다). "
                        "옛 자리 계산용으로만 남아 있다."},
        "p": P},
    "time": {
        "pos": _e(TIME_POS,
                  "시간줄 자리. row-bottom 은 하단 행을 셋으로 나눠 "
                  "날짜(왼)·am/pm(가운데)·시각(오른)을 따로 놓는다. top-* 는 "
                  "영역에 놓고, 자리가 없으면 아래로 흘려보내지 않고 그리지 "
                  "않는다(같은 기기에서 시간이 위아래를 오가면 안 된다)."),
        "fmts": {"t": "strs",
                 "help": "표기 형식. {h02} {m02} {M} {d} {am} {AM} 을 쓴다. "
                         "형식은 기기의 것이라 하나로 고정되고 숫자 내용만 "
                         "렌더마다 바뀐다."},
        "date_fmt": {"t": "str", "help": "row-bottom 의 날짜 조각 형식."},
        "hm_fmt": {"t": "str", "help": "row-bottom 의 시각 조각 형식."},
        "ampm": _n(0.3, 1.6, 0.02,
                   "row-bottom 의 am/pm 글자 높이 배수. 밑선을 맞춰 붙인다 — "
                   "보통 unit 의 h 와 같게 둔다."),
        "p": P},
    "mem": {"kind": _e(["M", "mem", "memory"], "메모리 표기 문자열."),
            "pos": _e(MEM_POS, "메모리 표기 자리."), "p": P},
    "meal": {"texts": {"t": "strs", "help": "식전·식후 표기(AC/PC 등)."},
             "p": P},
    "arrow": {"kinds": {"t": "enums", "opts": LCD_ICONS,
                        "help": "화살표 모양. meter=True 면 미터기 지시자라 "
                                "세로 자리가 혈당값으로 정해진다."},
              "gap": {"t": "nums", "n": 2, "min": 0, "max": 200, "step": 1,
                      "help": "숫자와의 간격 범위(px). meter=True 면 안 쓴다."},
              "p": P},
    "daterow": {"texts": {"t": "strs", "help": "날짜 줄 문자열."}, "p": P},
    "glulabel": {"texts": {"t": "strs", "help": "항목 이름 표기(GLU 등)."},
                 "p": P},
    "avgrow": {"p": P},
    "dotrow_above": {"texts": {"t": "strs",
                               "help": "숫자 위 보조 줄. dot_panel 인 기기만 "
                                       "도트로 그린다."}, "p": P},
    "dotrow_below": {"texts": {"t": "strs", "help": "숫자 아래 보조 줄."},
                     "p": P},
    "bezel": {"texts": {"t": "strs",
                        "help": "몸체(유리 밖)에 인쇄된 브랜드·모델명."},
              "edge": _e(BEZEL_EDGE, "어느 변에 찍히는가."),
              "ink": {"t": "num", "min": 0, "max": 255, "step": 5,
                      "help": "글자 밝기(0 검정 ~ 255 흰색). 없으면 몸체 "
                              "밝기에서 자동으로 정한다 — 검은 베젤 위 흰 "
                              "글씨인 기기는 여기서 235 쯤을 직접 준다."},
              "p": P},
    "dark_window": {
        "cover": _n(0.0, 1.0, 0.005,
                    "유리 바깥 검은 띠가 몸체 여백을 얼마나 덮는가. 1 에 "
                    "가까우면 전면이 검게 된다. 유리 '바깥'이라 요소 배치와는 "
                    "무관하다."),
        "tone": _n(0.0, 1.0, 0.005,
                   "띠의 어둡기(몸체 밝기 대비). 작을수록 더 검다.")},
}

# 요소가 아닌 낱값.
SCALARS = {
    "slots": _n(1, 6, 1,
                "숫자 칸 수. 값이 두 자리여도 칸은 그대로고 앞 칸이 빈다."),
    "align": _e(ALIGN,
                "값이 칸을 채우는 방향. 7-seg 는 오른쪽부터 채운다 — "
                "left/center 면 자릿수가 바뀔 때 숫자가 통째로 움직인다."),
    "italic": {"t": "bool", "help": "기울어진 세그먼트 글꼴."},
    "meter": {"t": "bool",
              "help": "미터기 기기. 화살표의 세로 자리가 혈당값에 대응하고, "
                      "유리 바깥에 검은 창이 깔린다."},
    "cell": _n(0.20, 0.90, 0.005,
               "칸 피치 / 숫자 높이. 작을수록 숫자가 커진다 — 칸이 폭을 꽉 "
               "채우므로 숫자 높이를 폭이 정한다: "
               "h = W / (칸수·cell·glyph + 자간 + 여백)."),
    "glyph": _n(0.40, 1.00, 0.005,
                "글리프 폭 / 칸 피치. 낮추면 글리프 모양은 그대로고 자간만 "
                "벌어진다(그만큼 숫자는 작아진다). 7-seg 는 글리프가 고정 "
                "너비라 늘려서 채우면 모양이 깨진다."),
    # dot_panel 은 노브에서 뺐다(2026-09-15). 선언한 기기가 하나도 없었고,
    # 사람이 실물과 대조해 "모든 기기가 seg 다"로 정했다. 켤 일이 없는
    # 스위치를 목록에 두면 "고쳐도 안 바뀐다"를 다시 겪는다.
}

# 체크박스로 새로 켤 때 들어가는 기본값.
TEMPLATES = {
    "unit": {"texts": ["mg/dL"], "pos": "below-right", "hug": 0.22, "p": 0.9},
    "time": {"pos": "below-left", "p": 0.85},
    "mem": {"kind": "M", "pos": "top-left", "p": 0.5},
    "meal": {"texts": ["AC", "PC"], "p": 0.3},
    "arrow": {"kinds": ["tri-right"], "gap": [2, 80], "p": 0.9},
    "daterow": {"p": 0.8},
    "glulabel": {"p": 0.6},
    "avgrow": {"p": 0.3},
    "dotrow_above": {"texts": ["--"], "p": 0.5},
    "dotrow_below": {"texts": ["--"], "p": 0.5},
    "bezel": {"texts": ["NAME"], "edge": "top", "p": 0.9},
    "icons": [["battery", "top-right", 1.0]],
    "dark_window": {"cover": 0.95, "tone": 0.22},
    "cell": 0.55,
    "glyph": 0.84,
    "meter": True,
}

ELEMENT_HELP = {
    "unit": "단위 표기(mg/dL). 숫자 아래에 놓인다.",
    "time": "시각 줄. row-bottom 을 고르면 날짜·am/pm·시각 세 칸이 된다.",
    "mem": "메모리 표기(M).",
    "meal": "식전·식후 표기.",
    "arrow": "화살표. meter 기기는 세로 자리가 혈당값을 가리킨다.",
    "daterow": "날짜 줄(시각과 별개 줄).",
    "glulabel": "항목 이름 표기(GLU 등).",
    "avgrow": "평균 줄(7 DAY AVG 등).",
    "dotrow_above": "숫자 위 보조 줄.",
    "dotrow_below": "숫자 아래 보조 줄.",
    "bezel": "몸체 인쇄(브랜드·모델명). 유리 밖이다.",
    "icons": "액정 아이콘 목록 — 줄마다 (종류, 자리, 확률).",
    "dark_window": "유리 바깥을 두르는 검은 베젤 띠.",
}


def schema():
    return {"regions": REGIONS_SCHEMA, "fields": FIELDS, "scalars": SCALARS,
            "templates": TEMPLATES, "element_help": ELEMENT_HELP,
            "icon_kinds": list(LCD_ICONS), "icon_pos": ICON_POS}

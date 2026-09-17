# validate_synth_panel.report_drops 의 시험.
#
# 왜 시험이 필요한가: 지금 합성기는 배치 실패를 내지 않는다(n=2000 seed 23000
# 에서 드롭 0). 그래서 기기 x 요소 분해를 인쇄하는 가지가 **한 번도 실행되지
# 않는다.** 실행되지 않는 보고 코드는 다음에 드롭이 생겼을 때 처음 돌고, 그때
# 틀려 있으면 진단이 아니라 방해가 된다([[metric-path-not-under-test]]).
#
# 그래서 가짜 매니페스트로 가지를 직접 돌린다.
#
#   python test_report_drops.py
import validate_synth_panel as V
import synth_profiles as SP


def rec(pid, dropped):
    return {"profile": pid, "dropped": list(dropped)}


def check(name, manifest, expect_fixed):
    print(f"\n--- {name} ---")
    got = V.report_drops(manifest)
    ok = got == expect_fixed
    print(f"  기기 고정 드롭 합계: {got} (기대 {expect_fixed}) "
          f"{'OK' if ok else 'FAIL'}")
    return ok


def main():
    # 상태성 요소는 장마다 꺼지는 것이 정상이라 합계에 안 들어간다.
    stateful = sorted(SP.STATEFUL_ELEMENTS)[0]
    assert stateful in SP.STATEFUL_ELEMENTS
    fixed = "unit"                      # 기기 고정 요소 예시(상태성 목록 밖)
    assert fixed not in SP.STATEFUL_ELEMENTS

    ok = True
    ok &= check("드롭 없음", [rec("a", []), rec("b", [])], 0)
    ok &= check("상태성만 빠짐 — 합계는 0 이어야 한다",
                [rec("a", [stateful]), rec("a", [stateful]), rec("b", [])], 0)
    ok &= check("기기 고정이 한 기기에서 계통적으로 빠짐",
                [rec("a", [fixed]) for _ in range(3)] + [rec("b", [])], 3)
    ok &= check("섞임 — 고정 2건 + 상태성 2건",
                [rec("a", [fixed, stateful]), rec("b", [fixed, stateful])], 2)

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

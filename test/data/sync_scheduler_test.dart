import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/sync/sync_engine.dart';
import 'package:sugarscan/data/sync/sync_scheduler.dart';

const _fast = Duration(milliseconds: 10);

void main() {
  test('연달아 부르면 한 번만 돈다', () async {
    var runs = 0;
    final scheduler = SyncScheduler(
      debounce: _fast,
      run: () async {
        runs++;
        return const SyncReport(outcome: SyncOutcome.ok);
      },
    );
    addTearDown(scheduler.dispose);

    scheduler
      ..schedule()
      ..schedule()
      ..schedule();

    await Future<void>.delayed(_fast * 5);

    // 기록을 연달아 세 건 저장해도 서버에는 한 번만 붙는다.
    expect(runs, 1);
  });

  // 두 회차가 겹치면 같은 아웃박스 항목을 두 번 보내고, 뒤늦게 끝난 쪽이
  // 이미 지워진 큐를 다시 지우려 든다.
  test('도는 중에 다시 부르면 겹쳐 돌지 않는다', () async {
    var runs = 0;
    final gate = Completer<void>();

    final scheduler = SyncScheduler(
      debounce: _fast,
      run: () async {
        runs++;
        if (runs == 1) await gate.future;
        return const SyncReport(outcome: SyncOutcome.ok);
      },
    );
    addTearDown(scheduler.dispose);

    final first = scheduler.now();
    final second = scheduler.now();

    expect(runs, 1, reason: '두 번째 호출은 새 회차를 시작하지 않는다');

    gate.complete();
    await Future.wait([first, second]);

    // 실행 중에 들어온 요청은 흘리지 않고, 끝난 뒤 한 번 더 돈다.
    expect(runs, 2);
  });

  test('결과를 흘려보낸다', () async {
    final scheduler = SyncScheduler(
      debounce: _fast,
      run: () async => const SyncReport(outcome: SyncOutcome.ok, pushed: 3),
    );
    addTearDown(scheduler.dispose);

    final seen = <SyncReport>[];
    final sub = scheduler.reports.listen(seen.add);
    addTearDown(sub.cancel);

    await scheduler.now();
    // 브로드캐스트 스트림은 한 박자 뒤에 전달한다.
    await pumpEventQueue();

    expect(seen.single.pushed, 3);
    expect(scheduler.lastReport?.pushed, 3);
  });

  test('정리한 뒤에는 예약이 실행되지 않는다', () async {
    var runs = 0;
    final scheduler = SyncScheduler(
      debounce: _fast,
      run: () async {
        runs++;
        return const SyncReport(outcome: SyncOutcome.ok);
      },
    )..schedule();

    scheduler.dispose();
    await Future<void>.delayed(_fast * 5);

    expect(runs, 0);
  });
}

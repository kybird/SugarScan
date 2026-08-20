import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

void main() {
  test('유휴 상태면 작업을 실행한다', () async {
    final throttler = FrameThrottler();
    final result = await throttler.run(() async => 42);

    expect(result, 42);
    expect(throttler.processedFrames, 1);
    expect(throttler.droppedFrames, 0);
  });

  test('처리 중이면 프레임을 버린다 — 큐에 쌓지 않는다', () async {
    final throttler = FrameThrottler();
    final gate = Completer<int>();

    final first = throttler.run(() => gate.future);
    // 첫 작업이 끝나기 전에 들어온 프레임들.
    final dropped1 = await throttler.run(() async => 1);
    final dropped2 = await throttler.run(() async => 2);

    expect(dropped1, isNull);
    expect(dropped2, isNull);
    expect(throttler.droppedFrames, 2);

    gate.complete(99);
    expect(await first, 99);
    expect(throttler.processedFrames, 1);
  });

  test('작업이 끝나면 다시 받는다', () async {
    final throttler = FrameThrottler();
    await throttler.run(() async => 1);
    final second = await throttler.run(() async => 2);

    expect(second, 2);
    expect(throttler.processedFrames, 2);
  });

  test('작업이 예외를 던져도 잠금이 풀린다', () async {
    final throttler = FrameThrottler();

    await expectLater(
      throttler.run(() async => throw StateError('boom')),
      throwsStateError,
    );
    expect(throttler.isBusy, isFalse);

    expect(await throttler.run(() async => 7), 7);
  });
}

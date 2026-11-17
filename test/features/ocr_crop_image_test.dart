import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/features/scan/ocr_crop_image.dart';
import 'package:sugarscan/ocr/ocr.dart';

/// 크롭 표시 위젯 — grayscale8 바이트를 화면에 그리는 경로와, 라이브 갱신 시
/// 디코드 낭비·이미지 누수 방지 장치(reset-on-change)의 뼈대.
void main() {
  OcrCrop cropOf({int? byteLength}) => OcrCrop(
    bytes: Uint8List.fromList(
      List<int>.filled(byteLength ?? 4 * 3, 200),
    ),
    width: 4,
    height: 3,
  );

  Future<void> pumpCrop(WidgetTester tester, OcrCrop crop) async {
    await tester.pumpWidget(
      MaterialApp(home: Scaffold(body: Center(child: OcrCropImage(crop: crop)))),
    );
    // dart:ui 디코드는 엔진의 실제 비동기 작업이라 가짜 시계 밖에서만
    // 완료된다. runAsync 로 실제 완료를 기다린 뒤 프레임을 그린다.
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 50)),
    );
    await tester.pump();
  }

  testWidgets('grayscale8 크롭을 디코드해 그린다', (tester) async {
    await pumpCrop(tester, cropOf());

    expect(find.byType(OcrCropImage), findsOneWidget);
    expect(find.byType(RawImage), findsOneWidget);
  });

  testWidgets('바이트 길이가 치수와 어긋난 크롭은 조용히 사라진다', (tester) async {
    // width*height 보다 짧은 버퍼 — 디코드가 실패하는 정상적 파손 경로.
    await pumpCrop(tester, cropOf(byteLength: 3));

    expect(find.byType(RawImage), findsNothing);
  });

  testWidgets('크롭이 바뀌면 새 이미지로 바뀐다', (tester) async {
    await pumpCrop(tester, cropOf());

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: OcrCropImage(crop: OcrCrop(bytes: Uint8List(12), width: 4, height: 3)),
          ),
        ),
      ),
    );
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 50)),
    );
    await tester.pump();

    expect(find.byType(RawImage), findsOneWidget);
  });
}

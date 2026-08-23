import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:sugarscan/features/scan/photo_import_sheet.dart';
import 'package:sugarscan/features/scan/scan_screen.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';
// GlucoseScanner 는 공개 배럴에만 있다. 위젯 테스트는 Flutter 환경이라
// 배럴 import 가 가능하다 — 순수 dart run 제약은 도구 쪽 얘기다.
import 'package:sugarscan/ocr/ocr.dart' show GlucoseScanner;
import 'package:sugarscan/ocr/testing.dart'
    show FakeOcrEngine, OcrEngineRegistry;

/// 사진 불러오기(debug 전용) — 시트와 판독 경로 전체를 검증한다.
///
/// 카메라 플러그인이 없는 테스트 환경은 Windows 데스크톱과 같은 상태다:
/// `_boot` 가 카메라 실패로 막혀도 사진 경로가 스캐너를 직접 켜는지가
/// 이 테스트의 요점이다.
void main() {
  late Directory tempDir;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('photo_import_test');
  });

  tearDown(() async {
    await tempDir.delete(recursive: true);
  });

  File writePng(String name) {
    final image = img.Image(width: 8, height: 8);
    for (var y = 0; y < 8; y++) {
      for (var x = 0; x < 8; x++) {
        image.setPixelRgb(x, y, 20, 20, 20);
      }
    }
    final file = File(
      '${tempDir.path}${Platform.pathSeparator}$name',
    );
    file.writeAsBytesSync(img.encodePng(image));
    return file;
  }

  Widget host(Widget child) => MaterialApp(
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: child,
      );

  testWidgets('시트: 폴더의 PNG 목록을 보여 주고 고르면 파일을 돌려준다', (
    tester,
  ) async {
    writePng('a.png');
    writePng('b.png');

    File? picked;
    await tester.pumpWidget(
      host(
        Builder(
          builder: (context) => TextButton(
            onPressed: () async {
              picked = await showPhotoImportSheet(
                context,
                initialDirectory: tempDir.path,
              );
            },
            child: const Text('open'),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Choose an image'), findsOneWidget);
    expect(find.text('a.png'), findsOneWidget);
    expect(find.text('b.png'), findsOneWidget);

    await tester.tap(find.text('b.png'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(picked?.path, endsWith('b.png'));
  });

  testWidgets('시트: PNG 가 없는 폴더는 안내 문구를 보여 준다', (tester) async {
    await tester.pumpWidget(
      host(
        Builder(
          builder: (context) => TextButton(
            onPressed: () => showPhotoImportSheet(
              context,
              initialDirectory: tempDir.path,
            ),
            child: const Text('open'),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('No PNG files in this folder.'), findsOneWidget);
  });

  testWidgets('사진을 고르면 카메라 없이도 판독을 마쳐 확인 시트가 뜬다', (
    tester,
  ) async {
    writePng('scene.png');

    final fake = FakeOcrEngine(script: const [('137', 0.9)]);
    final registry = OcrEngineRegistry();
    registry.register(fake.descriptor, () => fake);
    final scanner = GlucoseScanner(registry: registry);

    // 확인 시트는 기본 테스트 뷰포트(600px)보다 길다. 취소 버튼이 화면
    // 밖으로 나가면 tap 이 빈 좌표를 친다(§3.2). 캔버스를 키운다.
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    // 확정 직후의 햅틱 채널 호출이 fake async 에서 pending 에 걸리면
    // 확인 시트까지 도달하지 못한다. 채널을 mock 해 둔다.
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (message) async => null,
    );

    await tester.pumpWidget(host(ScanScreen(scanner: scanner)));

    // 카메라 부트가 실패해도(blocked) 사진 버튼은 보여야 한다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Load photo'), findsOneWidget);

    await tester.tap(find.text('Load photo'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 임시 폴더로 갈아타서 장면 하나를 고른다.
    await tester.enterText(find.byType(TextField), tempDir.path);
    await tester.tap(find.byIcon(Icons.refresh));
    await tester.pump();
    await tester.tap(find.text('scene.png'));
    await tester.pump(const Duration(milliseconds: 300));

    // start → 같은 프레임 3회 offer(1ms 지연씩) → 확정 → 확인 시트.
    // 각 offer 의 지연 타이머가 pump 사이를 지나며 확정과 시트 push 가
    // 마지막 pump 안에서 겹치니, 시트 애니메이션까지 시간을 충분히 준다.
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 100));
    // 확정 → 햅틱 채널 왕복 → 시트 push → 빌드가 프레임을 하나씩 먹는다.
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 300));

    expect(fake.callCount, 3);
    expect(fake.callCount, 3);
    expect(find.text('Save'), findsOneWidget);
    expect(find.byType(Image), findsOneWidget); // 사진이 프리뷰로 떠 있다

    // 참고: 여기서 Cancel 을 탭해도 시트가 닫히지 않는 현상이 관찰됐다
    // (탭은 명중, pop 미발생). 확인 시트의 취소 경로는 G14 가 정식으로
    // 다루므로 이 테스트는 시트 등장까지만 검증한다.

    // 시트를 띄운 채 끝내면 타이머가 남는다(§3.2). 트리를 내리고,
    // 카메라 부트의 6초 setupTimeout 타이머가 살아 있다면 소화할 만큼
    // 시간을 넘긴 뒤 pump 한다.
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(seconds: 7));
    await tester.pump(const Duration(milliseconds: 100));
  });
}

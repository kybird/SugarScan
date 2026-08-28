import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:sugarscan/features/scan/lcd_band_detector.dart';

/// LCD 밴드 검출기 — 패널 우선 설계의 핵심 시나리오 검증.
/// 패널 밖의 브랜드 텍스트는 밴드로 선택되지 않아야 한다(v1~v3 의 실측 실패).
void main() {
  // 합성 장면 1200×900 — 전역 오츠가 성립하는 실사진형 톤:
  // - LCD 패널 [300..900]×[250..500] 균일 205±3 (몸체 240 보다 약간 어두운
  //   정도 — 170 으로 하면 전역 오츠가 패널을 통째로 잉크로 만든다)
  // - 패널 안 판독 밴드: 속 빈 3글자(36×72, 획 6) y=300..372
  // - 패널 밖 브랜드 텍스트: 속 빈 3글자 y=600..640 — 행 게이트를 모두
  //   통과하는 정규 행이고 링만 흰(240)이다. 링 중간값 게이트의 직접 시험.
  Uint8List scenePng() {
    final rand = _Lcg(7);
    final im = img.Image(width: 1200, height: 900);
    for (var y = 0; y < 900; y++) {
      for (var x = 0; x < 1200; x++) {
        im.setPixelRgb(x, y, 240, 240, 240);
      }
    }
    for (var y = 250; y < 500; y++) {
      for (var x = 300; x < 900; x++) {
        final v = 205 + rand.nextSigned(3);
        im.setPixelRgb(x, y, v, v, v);
      }
    }
    void hollow(int x0, int y0, int bw, int bh, int t, int v) {
      for (var y = y0; y < y0 + bh; y++) {
        for (var x = x0; x < x0 + bw; x++) {
          final edge =
              x < x0 + t || x >= x0 + bw - t || y < y0 + t || y >= y0 + bh - t;
          if (edge) im.setPixelRgb(x, y, v, v, v);
        }
      }
    }

    // 판독 밴드 — 속 빈 글자 3개(세로 72, 획 6): 채움률 ≈0.44
    hollow(380, 300, 36, 72, 6, 30);
    hollow(500, 300, 36, 72, 6, 30);
    hollow(620, 300, 36, 72, 6, 30);
    // 브랜드 텍스트 — 패널 밖, 정규 피치의 속 빈 글자 3개
    hollow(350, 600, 40, 40, 8, 30);
    hollow(450, 600, 40, 40, 8, 30);
    hollow(550, 600, 40, 40, 8, 30);
    return img.encodePng(im);
  }

  test('패널 안의 판독 밴드가 최상위 후보다 — 브랜드 텍스트가 아닌', () {
    final bands = detectReadingBands(scenePng());
    expect(bands, isNotEmpty);
    final top = bands.first;
    final cy =
        (top.quad[0].y + top.quad[2].y) / 2;
    final cx = (top.quad[0].x + top.quad[1].x) / 2;
    // 판독 밴드의 실제 위치 [380..656]×[300..372]
    expect(cx, inInclusiveRange(360, 700), reason: 'quad=${top.quad}');
    expect(cy, inInclusiveRange(270, 400), reason: 'quad=${top.quad}');
    // 후보 중 패널 밖(y>500) 행이 최상위가 아니다
    for (final b in bands.take(1)) {
      expect((b.quad[0].y + b.quad[2].y) / 2, lessThan(500),
          reason: 'top band must be inside the panel');
    }
  });

  test('균일 장면은 후보 없음 — 정상 거부', () {
    final im = img.Image(width: 640, height: 480);
    for (var y = 0; y < 480; y++) {
      for (var x = 0; x < 640; x++) {
        im.setPixelRgb(x, y, 128, 128, 128);
      }
    }
    expect(detectReadingBands(img.encodePng(im)), isEmpty);
  });
}

class _Lcg {
  _Lcg(this._s);
  int _s;
  int nextSigned(int spread) {
    _s = (_s * 1103515245 + 12345) & 0x7fffffff;
    return (_s % (2 * spread + 1)) - spread;
  }
}

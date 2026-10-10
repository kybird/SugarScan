import 'dart:math' as math;
import 'dart:typed_data';

/// BandNet 검출기의 상수와 디코드 — ONNX 그래프 밖에서 돌는 순수 계산.
///
/// 수식은 학습 쪽 정본(`assets_dev/train/band_net.py` decode ·
/// `eval_e2e_bandnet.py` 의 게이트)과 같다. 여기가 어긋나면 모델이 맞아도
/// 상자가 틀린다.
abstract final class BandDetector {
  /// 검출기 입력 한 변. 프리징 스택(ftk5_g0.06)의 size.
  static const int inputSize = 640;

  /// 헤드 특징맵 스트라이드. 체크포인트의 stride 와 같다.
  static const int stride = 16;

  /// 특징맵 한 변 = inputSize / stride.
  static const int gridSize = inputSize ~/ stride; // 40

  /// objectness 확신 게이트. eval_e2e_bandnet.py --conf 기본값.
  static const double confidenceGate = 0.25;

  /// 예측 면적/화면 하한. 초원경 스케일 오탐을 막는 게이트다.
  static const double minAreaFraction = 0.02;

  /// obj logit 맵(1600)과 reg 거리 맵(6400, 채널 우선)을 원본 좌표 상자로.
  ///
  /// obj 는 sigmoid 전 logit 이다(그래프가 sigmoid 를 내지 않는다).
  /// reg 는 softplus 가 이미 적용된 칸 중심→네 변 거리(l,t,r,b).
  /// 게이트(확신·면적)를 통과하지 못하면 null.
  static BandBox? decode(
    Float32List objLogits,
    Float32List regDistances, {
    required double scale,
    required int dx,
    required int dy,
    required int imageWidth,
    required int imageHeight,
  }) {
    final cells = gridSize * gridSize;
    var idx = 0;
    var best = objLogits[0];
    for (var i = 1; i < objLogits.length; i++) {
      if (objLogits[i] > best) {
        best = objLogits[i];
        idx = i;
      }
    }
    final score = 1 / (1 + math.exp(-best));
    if (score < confidenceGate) return null;

    final gx = idx % gridSize;
    final gy = idx ~/ gridSize;
    final cx = (gx + 0.5) * stride;
    final cy = (gy + 0.5) * stride;
    // reg 플랫 배열은 채널 우선: [l 1600개, t 1600개, r 1600개, b 1600개].
    final left = cx - regDistances[idx];
    final top = cy - regDistances[cells + idx];
    final right = cx + regDistances[2 * cells + idx];
    final bottom = cy + regDistances[3 * cells + idx];

    // 레터박스 좌표 -> 원본 좌표.
    final l = (left - dx) / scale;
    final t = (top - dy) / scale;
    final r = (right - dx) / scale;
    final b = (bottom - dy) / scale;
    final fraction =
        (r - l) * (b - t) / (imageWidth * imageHeight);
    if (fraction < minAreaFraction) return null;

    return BandBox(score: score, left: l, top: t, right: r, bottom: b);
  }

  /// 원본 좌표 상자를 리더 크롭 직사각형으로 — eval_e2e_bandnet.py 의
  /// 좌표 변환(int·round·clamp) 과 같은 반올림. 너무 작으면 null.
  static ({int x0, int y0, int x1, int y1})? cropRect(
    BandBox box,
    int imageWidth,
    int imageHeight,
  ) {
    final x0 = math.max(0, box.left.truncate());
    final y0 = math.max(0, box.top.truncate());
    final x1 = math.min(imageWidth, _pythonRound(box.right));
    final y1 = math.min(imageHeight, _pythonRound(box.bottom));
    if (x1 - x0 < 4 || y1 - y0 < 4) return null;
    return (x0: x0, y0: y0, x1: x1, y1: y1);
  }

  /// Python round 와 같은 반올림(절반은 짝수로).
  static int _pythonRound(double x) {
    final floor = x.floorToDouble();
    final diff = x - floor;
    if (diff > 0.5) return floor.toInt() + 1;
    if (diff < 0.5) return floor.toInt();
    return floor.toInt() % 2 == 0 ? floor.toInt() : floor.toInt() + 1;
  }
}

/// 검출된 숫자 밴드. 좌표는 원본 이미지 픽셀 좌표계.
final class BandBox {
  const BandBox({
    required this.score,
    required this.left,
    required this.top,
    required this.right,
    required this.bottom,
  });

  /// sigmoid(obj) 0~1.
  final double score;
  final double left;
  final double top;
  final double right;
  final double bottom;
}

import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../../domain/models/glucose_unit.dart';
import '../../ocr/ocr.dart';

/// 사진을 손으로 움직여 가이드 박스에 맞추는 **디버그 전용** 화면.
///
/// 왜 필요한가: 앱의 판독 경로는 "사용자가 가이드 박스에 화면을 맞춘다" 를
/// 전제로 하고, 엔진은 그 박스 안만 본다(`roi: guideBoxFor`). 그런데
/// 실기기 없이는 그 전제를 시험할 방법이 없었다. 기존 사진 불러오기는
/// `preprocessPhotoForEngine` 로 **자동 정렬**을 거치므로, 정렬이 맞고 틀림에
/// 따라 판독이 어떻게 달라지는지를 볼 수 없다.
///
/// 이 화면은 자동 정렬을 쓰지 않는다. 화면에 **보이는 그대로**를 캡처해
/// 카메라와 같은 `roi` 로 엔진에 넘긴다 — 겨냥한 결과가 곧 입력이다.
class PhotoAlignScreen extends StatefulWidget {
  const PhotoAlignScreen({
    super.key,
    required this.imageBytes,
    required this.scanner,
    required this.unit,
  });

  final Uint8List imageBytes;
  final GlucoseScanner scanner;

  /// 값 검증 기준. 스캐너가 이 단위를 읽을 수 있는 엔진을 고른다.
  final GlucoseUnit unit;

  @override
  State<PhotoAlignScreen> createState() => _PhotoAlignScreenState();
}

class _PhotoAlignScreenState extends State<PhotoAlignScreen> {
  final GlobalKey _captureKey = GlobalKey();

  ui.Image? _image;
  Offset _offset = Offset.zero;
  double _scale = 1;
  double _rotation = 0; // 라디안
  bool _flipH = false;

  /// 프레임 종횡비(세로/가로). 카메라 경로가 프리뷰를 이 비율로 묶으므로
  /// 여기서도 같게 묶어야 가이드 박스의 **실제 모양**이 같아진다.
  double _frameAspect = 9 / 16;
  ScanOutcome? _outcome;
  bool _busy = false;

  Offset _focalStart = Offset.zero;
  Offset _offsetStart = Offset.zero;
  double _scaleStart = 1;

  @override
  void initState() {
    super.initState();
    _decode();
  }

  Future<void> _decode() async {
    final codec = await ui.instantiateImageCodec(widget.imageBytes);
    final frame = await codec.getNextFrame();
    if (!mounted) {
      frame.image.dispose();
      return;
    }
    setState(() => _image = frame.image);
  }

  @override
  void dispose() {
    _image?.dispose();
    super.dispose();
  }

  void _nudge(double dx, double dy) =>
      setState(() => _offset += Offset(dx, dy));

  /// [anchor] 를 화면상 같은 자리에 붙들어 둔 채로 배율만 바꾼다.
  ///
  /// 중심 기준으로 확대하면 가이드 박스에 겨우 맞춰 놓은 숫자가 화면 밖으로
  /// 달아난다. 확대할수록 다시 맞추기 어려워져 이 화면의 목적이 사라진다.
  void _zoomAt(double factor, Offset anchor, Size viewport) {
    setState(() {
      final next = (_scale * factor).clamp(0.1, 8.0);
      final applied = next / _scale;
      // 변환이 중심(alignment: center) 기준이라 중심으로부터의 변위로 푼다.
      final center = Offset(viewport.width / 2, viewport.height / 2);
      _offset = anchor - center - (anchor - center - _offset) * applied;
      _scale = next;
    });
  }

  void _rotate(double degrees) =>
      setState(() => _rotation += degrees * math.pi / 180);

  void _reset() => setState(() {
    _offset = Offset.zero;
    _scale = 1;
    _rotation = 0;
    _flipH = false;
    _outcome = null;
  });

  /// 화면에 보이는 그대로를 캡처해 엔진에 넘긴다.
  ///
  /// 자동 정렬을 거치지 않는 것이 이 화면의 핵심이다. 캡처본을 카메라와 같은
  /// [NormalizedRect.guideBoxFor] 로 잘라 읽으므로, 정렬이 어긋나면 어긋난
  /// 대로 결과가 나온다 — 그것이 확인하려는 것이다.
  Future<void> _read() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final boundary =
          _captureKey.currentContext?.findRenderObject()
              as RenderRepaintBoundary?;
      if (boundary == null) return;

      final shot = await boundary.toImage();
      final data = await shot.toByteData(format: ui.ImageByteFormat.png);
      final width = shot.width;
      final height = shot.height;
      shot.dispose();
      if (data == null || !mounted) return;

      // 엔진은 세션이 시작돼 있어야 값을 낸다. 카메라 경로와 같은 순서다.
      final started = await widget.scanner.start(unit: widget.unit);
      if (started is ScanUnavailable) {
        if (mounted) setState(() => _outcome = started);
        return;
      }

      final frame = OcrFrame(
        bytes: data.buffer.asUint8List(),
        format: OcrImageFormat.png,
        width: width,
        height: height,
        roi: NormalizedRect.guideBoxFor(_frameAspect),
      );

      // 정지 사진이라 프레임이 한 종류다. 카메라와 같은 확정 조건(프레임 합의)
      // 을 지나게 하려고 같은 프레임을 반복해 넣는다.
      ScanOutcome? last;
      for (var i = 0; i < 3; i++) {
        last = await widget.scanner.offer(frame);
        if (last is ScanConfirmed) break;
      }
      if (mounted) setState(() => _outcome = last);
    } finally {
      await widget.scanner.stop();
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final image = _image;
    return Scaffold(
      appBar: AppBar(
        title: const Text('사진 정렬 테스트 (디버그)'),
        actions: [
          IconButton(
            onPressed: _reset,
            icon: const Icon(Icons.restart_alt),
            tooltip: '원래대로',
          ),
        ],
      ),
      body: image == null
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Expanded(
                  // 카메라 경로와 **같은 비율로 묶는다.**
                  //
                  // 가이드 박스는 `0.80 × 0.20` 이라는 정규화 값이라 그 자체로는
                  // 모양이 없다 — 프레임이 9:16 이면 2.25:1, 창이 가로면 8:1 이
                  // 된다. 여기서 묶지 않으면 화면의 박스와 엔진이 보는 ROI 가
                  // 가리키는 모양이 달라지고, 그 어긋남은 "그냥 인식이 안 된다"
                  // 로만 보인다.
                  child: Center(
                    child: AspectRatio(
                      aspectRatio: _frameAspect,
                      child: LayoutBuilder(
                        builder: (context, constraints) => Listener(
                          // 데스크톱에는 핀치가 없다. 휠이 유일한 확대 수단이라
                          // 여기서 막으면 이 화면은 배율 1 에서만 쓸 수 있다.
                          onPointerSignal: (signal) {
                            if (signal is! PointerScrollEvent) return;
                            _zoomAt(
                              signal.scrollDelta.dy < 0 ? 1.1 : 1 / 1.1,
                              signal.localPosition,
                              constraints.biggest,
                            );
                          },
                          child: GestureDetector(
                            onScaleStart: (d) {
                              _focalStart = d.localFocalPoint;
                              _offsetStart = _offset;
                              _scaleStart = _scale;
                            },
                            onScaleUpdate: (d) => setState(() {
                              _scale = (_scaleStart * d.scale).clamp(0.1, 8.0);
                              _offset =
                                  _offsetStart +
                                  (d.localFocalPoint - _focalStart);
                            }),
                            child: RepaintBoundary(
                              key: _captureKey,
                              child: ClipRect(
                                child: SizedBox(
                                  width: constraints.maxWidth,
                                  height: constraints.maxHeight,
                                  child: ColoredBox(
                                    color: Colors.black,
                                    child: Stack(
                                      fit: StackFit.expand,
                                      children: [
                                        Transform(
                                          alignment: Alignment.center,
                                          transform: Matrix4.identity()
                                            ..translateByDouble(
                                              _offset.dx,
                                              _offset.dy,
                                              0,
                                              1,
                                            )
                                            ..rotateZ(_rotation)
                                            ..scaleByDouble(
                                              _flipH ? -_scale : _scale,
                                              _scale,
                                              1,
                                              1,
                                            ),
                                          child: RawImage(
                                            image: image,
                                            fit: BoxFit.contain,
                                          ),
                                        ),
                                        // 가이드 박스 — 카메라 화면과 같은 좌표.
                                        // 캡처본에도 선이 함께 찍히지만 엔진은 이
                                        // 사각형 **안쪽**만 보므로 판독에 닿지 않는다.
                                        CustomPaint(
                                          painter: _GuidePainter(
                                            NormalizedRect.guideBoxFor(
                                              _frameAspect,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                _Controls(
                  onNudge: _nudge,
                  onRotate: _rotate,
                  onFlip: () => setState(() => _flipH = !_flipH),
                  onRead: _busy ? null : _read,
                  rotation: _rotation,
                  scale: _scale,
                  frameAspect: _frameAspect,
                  onFrameAspect: (v) => setState(() => _frameAspect = v),
                  onZoom: (f) =>
                      setState(() => _scale = (_scale * f).clamp(0.1, 8.0)),
                ),
                _OutcomeBar(outcome: _outcome, busy: _busy),
              ],
            ),
    );
  }
}

class _GuidePainter extends CustomPainter {
  const _GuidePainter(this.roi);

  final NormalizedRect roi;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(
      Rect.fromLTWH(
        roi.left * size.width,
        roi.top * size.height,
        roi.width * size.width,
        roi.height * size.height,
      ),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = const Color(0xFFFFD23F),
    );
  }

  @override
  bool shouldRepaint(covariant _GuidePainter oldDelegate) =>
      oldDelegate.roi != roi;
}

class _Controls extends StatelessWidget {
  const _Controls({
    required this.onNudge,
    required this.onRotate,
    required this.onFlip,
    required this.onRead,
    required this.rotation,
    required this.scale,
    required this.frameAspect,
    required this.onFrameAspect,
    required this.onZoom,
  });

  final void Function(double dx, double dy) onNudge;
  final void Function(double degrees) onRotate;
  final VoidCallback onFlip;
  final VoidCallback? onRead;
  final double rotation;
  final double scale;
  final double frameAspect;
  final ValueChanged<double> onFrameAspect;
  final ValueChanged<double> onZoom;

  @override
  Widget build(BuildContext context) {
    const step = 12.0;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Column(
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            alignment: WrapAlignment.center,
            children: [
              IconButton.filledTonal(
                onPressed: () => onNudge(0, -step),
                icon: const Icon(Icons.keyboard_arrow_up),
                tooltip: '위로',
              ),
              IconButton.filledTonal(
                onPressed: () => onNudge(0, step),
                icon: const Icon(Icons.keyboard_arrow_down),
                tooltip: '아래로',
              ),
              IconButton.filledTonal(
                onPressed: () => onNudge(-step, 0),
                icon: const Icon(Icons.keyboard_arrow_left),
                tooltip: '왼쪽으로',
              ),
              IconButton.filledTonal(
                onPressed: () => onNudge(step, 0),
                icon: const Icon(Icons.keyboard_arrow_right),
                tooltip: '오른쪽으로',
              ),
              IconButton.filledTonal(
                onPressed: () => onRotate(-90),
                icon: const Icon(Icons.rotate_left),
                tooltip: '왼쪽 90°',
              ),
              IconButton.filledTonal(
                onPressed: () => onRotate(90),
                icon: const Icon(Icons.rotate_right),
                tooltip: '오른쪽 90°',
              ),
              IconButton.filledTonal(
                onPressed: () => onRotate(-2),
                icon: const Icon(Icons.turn_left),
                tooltip: '왼쪽 2°',
              ),
              IconButton.filledTonal(
                onPressed: () => onRotate(2),
                icon: const Icon(Icons.turn_right),
                tooltip: '오른쪽 2°',
              ),
              IconButton.filledTonal(
                onPressed: onFlip,
                icon: const Icon(Icons.flip),
                tooltip: '좌우 반전',
              ),
              IconButton.filledTonal(
                onPressed: () => onZoom(1 / 1.1),
                icon: const Icon(Icons.zoom_out),
                tooltip: '축소',
              ),
              IconButton.filledTonal(
                onPressed: () => onZoom(1.1),
                icon: const Icon(Icons.zoom_in),
                tooltip: '확대',
              ),
              // 센서 비율에 따라 가이드 박스의 **실제 모양**이 달라진다.
              // 16:9 센서면 2.25:1, 4:3 센서면 3.00:1 이다. 기기마다
              // 다르므로 둘 다 볼 수 있게 둔다.
              SegmentedButton<double>(
                segments: const [
                  ButtonSegment(value: 9 / 16, label: Text('9:16')),
                  ButtonSegment(value: 3 / 4, label: Text('3:4')),
                ],
                selected: {frameAspect},
                onSelectionChanged: (v) => onFrameAspect(v.first),
                showSelectedIcon: false,
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(
                  '회전 ${(rotation * 180 / math.pi).toStringAsFixed(1)}° · '
                  '배율 ${scale.toStringAsFixed(2)}× · 가이드 박스 '
                  '${(NormalizedRect.digitCellAspect * NormalizedRect.guideDigitCount).toStringAsFixed(2)}:1 · '
                  '드래그 이동 · 휠 확대',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              FilledButton.icon(
                onPressed: onRead,
                icon: const Icon(Icons.center_focus_strong),
                label: const Text('판독'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _OutcomeBar extends StatelessWidget {
  const _OutcomeBar({required this.outcome, required this.busy});

  final ScanOutcome? outcome;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final outcome = this.outcome;

    final (String text, Color color) = switch (outcome) {
      _ when busy => ('판독 중…', scheme.surfaceContainerHighest),
      null => ('가이드 박스에 화면을 맞춘 뒤 "판독" 을 누른다', scheme.surfaceContainerHighest),
      // 이 화면은 진단용이라 원문(rawText)까지 보여준다. 어떤 글자를 읽고
      // 어떤 값으로 확정했는지가 갈리는 지점을 봐야 하기 때문이다.
      ScanConfirmed(
        :final value,
        :final unit,
        :final rawText,
        :final engineId,
      ) =>
        (
          '확정 $value ${unit.name} · 원문 "$rawText" · $engineId',
          scheme.primaryContainer,
        ),
      ScanRejected(:final reason) => (
        '거절: ${reason.name}',
        scheme.errorContainer,
      ),
      ScanUnavailable(:final reason) => (
        '엔진 없음: ${reason.name}',
        scheme.errorContainer,
      ),
      ScanScanning(:final previewValue) => (
        '읽는 중 — 확정 안 됨${previewValue == null ? '' : ' (미리보기 $previewValue)'}',
        scheme.surfaceContainerHighest,
      ),
      ScanIdle() => ('대기', scheme.surfaceContainerHighest),
    };

    return Container(
      width: double.infinity,
      color: color,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Text(text, style: theme.textTheme.bodyMedium),
    );
  }
}

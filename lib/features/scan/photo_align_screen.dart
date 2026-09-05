import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../../domain/models/glucose_unit.dart';
import '../../ocr/ocr.dart';

/// 사진을 손으로 움직여 가이드 박스에 맞추는 **디버그 전용** 화면.
///
/// 왜 필요한가: 앱의 판독 경로는 "사용자가 가이드 박스에 화면을 맞춘다" 를
/// 전제로 하고, 엔진은 그 박스 안만 본다(`roi: defaultGuideBox`). 그런데
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
  /// [NormalizedRect.defaultGuideBox] 로 잘라 읽으므로, 정렬이 어긋나면 어긋난
  /// 대로 결과가 나온다 — 그것이 확인하려는 것이다.
  Future<void> _read() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final boundary =
          _captureKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
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
        roi: NormalizedRect.defaultGuideBox,
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
                  child: LayoutBuilder(
                    builder: (context, constraints) => GestureDetector(
                      onScaleStart: (d) {
                        _focalStart = d.localFocalPoint;
                        _offsetStart = _offset;
                        _scaleStart = _scale;
                      },
                      onScaleUpdate: (d) => setState(() {
                        _scale = (_scaleStart * d.scale).clamp(0.1, 8.0);
                        _offset = _offsetStart + (d.localFocalPoint - _focalStart);
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
                                          _offset.dx, _offset.dy, 0, 1)
                                      ..rotateZ(_rotation)
                                      ..scaleByDouble(
                                          _flipH ? -_scale : _scale,
                                          _scale, 1, 1),
                                    child: RawImage(image: image, fit: BoxFit.contain),
                                  ),
                                  // 가이드 박스 — 카메라 화면과 같은 좌표.
                                  // 캡처본에도 선이 함께 찍히지만 엔진은 이
                                  // 사각형 **안쪽**만 보므로 판독에 닿지 않는다.
                                  CustomPaint(
                                    painter: const _GuidePainter(
                                      NormalizedRect.defaultGuideBox,
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
                _Controls(
                  onNudge: _nudge,
                  onRotate: _rotate,
                  onFlip: () => setState(() => _flipH = !_flipH),
                  onRead: _busy ? null : _read,
                  rotation: _rotation,
                  scale: _scale,
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
  });

  final void Function(double dx, double dy) onNudge;
  final void Function(double degrees) onRotate;
  final VoidCallback onFlip;
  final VoidCallback? onRead;
  final double rotation;
  final double scale;

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
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(
                  '회전 ${(rotation * 180 / math.pi).toStringAsFixed(1)}° · '
                  '배율 ${scale.toStringAsFixed(2)}× · 드래그 이동 · 핀치 확대',
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
      null => (
          '가이드 박스에 화면을 맞춘 뒤 "판독" 을 누른다',
          scheme.surfaceContainerHighest,
        ),
      // 이 화면은 진단용이라 원문(rawText)까지 보여준다. 어떤 글자를 읽고
      // 어떤 값으로 확정했는지가 갈리는 지점을 봐야 하기 때문이다.
      ScanConfirmed(:final value, :final unit, :final rawText, :final engineId) =>
        ('확정 $value ${unit.name} · 원문 "$rawText" · $engineId',
            scheme.primaryContainer),
      ScanRejected(:final reason) => ('거절: ${reason.name}', scheme.errorContainer),
      ScanUnavailable(:final reason) =>
        ('엔진 없음: ${reason.name}', scheme.errorContainer),
      ScanScanning(:final previewValue) =>
        ('읽는 중 — 확정 안 됨${previewValue == null ? '' : ' (미리보기 $previewValue)'}',
            scheme.surfaceContainerHighest),
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

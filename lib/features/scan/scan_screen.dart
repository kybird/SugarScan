import 'dart:io' show Platform;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../domain/models/glucose_unit.dart';
import '../../domain/models/reading_source.dart';
import '../../domain/services/tag_suggester.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../ocr/ocr.dart';
import 'camera_image_adapter.dart';
import 'confirm_sheet.dart';
import 'manual_entry_sheet.dart';
import 'scan_entry.dart';

/// 카메라 스캐너 화면.
///
/// 이 화면이 하는 일은 프레임을 [GlucoseScanner] 에 밀어 넣고 돌아온 결과를
/// 그리는 것뿐이다. 글자 보정도, 값 검증도, 프레임 합의도 하지 않는다 —
/// 전부 OCR 모듈 안에서 끝난다.
///
/// 저장 결과를 [ScanEntry] 로 pop 한다. 영속화는 W8 에서 붙는다.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> with WidgetsBindingObserver {
  /// 카메라 준비를 기다리는 한도.
  ///
  /// 드물게 카메라 서비스가 응답하지 않는 기기가 있다. 무한정 기다리면
  /// 사용자는 도는 표시기만 보게 되므로, 끊고 수동 입력으로 안내한다.
  static const Duration _setupTimeout = Duration(seconds: 6);

  final GlucoseScanner _scanner = buildGlucoseScanner();

  CameraController? _controller;
  int _rotationDegrees = 0;
  GlucoseUnit _unit = GlucoseUnit.mgdl;

  ScanOutcome _outcome = const ScanIdle();

  /// 확인 시트가 떠 있는 동안에는 프레임을 흘려보낸다.
  bool _paused = false;
  bool _streaming = false;

  /// 스캔 자체가 불가능한 상태. null 이면 정상.
  String? _blockedMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // 첫 프레임 이후로 미룬다. initState 시점에는 Localizations 같은 상속
    // 위젯을 읽을 수 없다.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _boot();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _teardown();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // 앱이 백그라운드로 가면 OS 가 카메라를 회수한다. 붙잡고 있으면
    // 복귀 시 프리뷰가 검은 화면으로 남는다.
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;

    if (state == AppLifecycleState.inactive) {
      _stopStream();
      controller.dispose();
      _controller = null;
    } else if (state == AppLifecycleState.resumed) {
      _boot();
    }
  }

  Future<void> _boot() async {
    final l10n = AppLocalizations.of(context);
    _unit = defaultUnitForCountry(
      WidgetsBinding.instance.platformDispatcher.locale.countryCode,
    );

    try {
      final cameras = await availableCameras().timeout(_setupTimeout);
      if (cameras.isEmpty) {
        _block(l10n.scanUnavailable);
        return;
      }
      final camera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      _rotationDegrees = uprightRotationFor(camera);

      final controller = CameraController(
        camera,
        ResolutionPreset.high,
        enableAudio: false,
        // Android 는 Y 평면만 꺼내 쓰고, iOS 는 BGRA 를 휘도로 바꾼다.
        imageFormatGroup:
            Platform.isAndroid ? ImageFormatGroup.yuv420 : ImageFormatGroup.bgra8888,
      );
      await controller.initialize().timeout(_setupTimeout);
      if (!mounted) {
        await controller.dispose();
        return;
      }
      _controller = controller;

      final outcome = await _scanner.start(unit: _unit);
      if (!mounted) return;

      if (outcome is ScanUnavailable) {
        // 모델이 없거나 단위를 읽을 수 있는 엔진이 없다. 수동 입력으로 안내한다.
        _block(l10n.scanUnavailable);
        return;
      }

      setState(() {
        _outcome = outcome;
        _blockedMessage = null;
      });
      await _startStream();
    } on CameraException catch (error) {
      _block(
        error.code == 'CameraAccessDenied'
            ? l10n.cameraPermissionRequired
            : l10n.scanUnavailable,
      );
    } on Object {
      _block(l10n.scanUnavailable);
    }
  }

  void _block(String message) {
    if (!mounted) return;
    setState(() => _blockedMessage = message);
  }

  Future<void> _startStream() async {
    final controller = _controller;
    if (controller == null || _streaming) return;
    _streaming = true;
    await controller.startImageStream(_onFrame);
  }

  Future<void> _stopStream() async {
    final controller = _controller;
    if (controller == null || !_streaming) return;
    _streaming = false;
    try {
      await controller.stopImageStream();
    } on Object {
      // 이미 멈춘 스트림을 다시 멈추는 경우. 무시해도 안전하다.
    }
  }

  Future<void> _onFrame(CameraImage image) async {
    if (_paused || !mounted) return;

    final frame = ocrFrameFromCameraImage(
      image,
      rotationDegrees: _rotationDegrees,
      roi: NormalizedRect.defaultGuideBox,
    );
    if (frame == null) return;

    // 스캐너가 스스로 유량을 조절한다. 추론 중이면 프레임을 버리고 직전
    // 상태를 그대로 돌려주므로, 화면은 드롭 여부를 알 필요가 없다.
    final outcome = await _scanner.offer(frame);
    if (!mounted || _paused) return;

    setState(() => _outcome = outcome);
    if (outcome is ScanConfirmed) {
      await _handleConfirmed(outcome);
    }
  }

  Future<void> _handleConfirmed(ScanConfirmed confirmed) async {
    _paused = true;
    await _stopStream();
    await HapticFeedback.mediumImpact();
    if (!mounted) return;

    final entry = ScanEntry(
      value: confirmed.value,
      unit: confirmed.unit,
      tag: const TagSuggester().suggest(TagContext(localNow: DateTime.now())),
      source: ReadingSource.ocr,
      engineId: confirmed.engineId,
      confidence: confirmed.confidence,
      rawText: confirmed.rawText,
    );

    final saved = await showConfirmSheet(context, entry: entry);
    if (!mounted) return;

    if (saved != null) {
      Navigator.of(context).pop(saved);
      return;
    }

    // 취소했으면 처음부터 다시 읽는다. 이전 프레임 합의는 버린다.
    _scanner.reset();
    _paused = false;
    setState(() => _outcome = _scanner.lastOutcome);
    await _startStream();
  }

  /// 직접 입력. 스캔이 막혔든 아니든 언제나 열 수 있다.
  Future<void> _openManualEntry() async {
    _paused = true;
    await _stopStream();
    if (!mounted) return;

    final entry = await showManualEntrySheet(context, unit: _unit);
    if (!mounted) return;

    if (entry != null) {
      Navigator.of(context).pop(entry);
      return;
    }

    _scanner.reset();
    _paused = false;
    setState(() => _outcome = _scanner.lastOutcome);
    await _startStream();
  }

  Future<void> _teardown() async {
    await _stopStream();
    await _controller?.dispose();
    _controller = null;
    await _scanner.stop();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        title: Text(l10n.scanTitle),
      ),
      extendBodyBehindAppBar: true,
      body: Stack(
        fit: StackFit.expand,
        children: [
          const ColoredBox(color: Color(0xFF101214)),
          if (_blockedMessage == null) _buildPreview(),
          _buildFooter(l10n),
        ],
      ),
    );
  }

  Widget _buildPreview() {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    // 프리뷰와 가이드 박스를 같은 상자 안에 겹쳐 그려야 화면의 사각형과
    // 프레임의 ROI 가 같은 영역을 가리킨다.
    //
    // 다만 센서 종횡비와 회전 보정 때문에 완전히 일치한다고 단정할 수 없다.
    // 실기기에서 눈으로 맞춰 보정해야 하는 부분이다(W2 잔여 과제).
    return Center(
      child: AspectRatio(
        aspectRatio: controller.value.aspectRatio,
        child: Stack(
          fit: StackFit.expand,
          children: [
            CameraPreview(controller),
            _GuideBoxOverlay(
              roi: NormalizedRect.defaultGuideBox,
              outcome: _outcome,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFooter(AppLocalizations l10n) {
    return Align(
      alignment: Alignment.bottomCenter,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _statusText(l10n),
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 15),
              ),
              const SizedBox(height: 16),
              // OCR 이 성공하든 실패하든 이 버튼은 항상 보인다.
              // 사용자가 기록을 남기지 못하는 상태를 만들지 않는다.
              OutlinedButton.icon(
                onPressed: _openManualEntry,
                icon: const Icon(Icons.keyboard),
                label: Text(l10n.manualEntryCta),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Colors.white54),
                  minimumSize: const Size(0, 48),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _statusText(AppLocalizations l10n) {
    if (_blockedMessage != null) return _blockedMessage!;

    return switch (_outcome) {
      ScanRejected(:final reason) => switch (reason) {
          ScanRejectionReason.meterHigh => l10n.meterShowsHigh,
          ScanRejectionReason.meterLow => l10n.meterShowsLow,
        },
      ScanUnavailable() => l10n.scanUnavailable,
      ScanScanning(:final previewValue) when previewValue != null =>
        l10n.scanReading,
      _ => l10n.scanGuideHint,
    };
  }
}

/// 가이드 박스. 이 영역이 곧 OCR 의 ROI 이며, 덕분에 텍스트 검출 단계를
/// 생략할 수 있다. 테두리 색으로 인식 진행 상태를 알린다.
class _GuideBoxOverlay extends StatelessWidget {
  const _GuideBoxOverlay({required this.roi, required this.outcome});

  final NormalizedRect roi;
  final ScanOutcome outcome;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    final (color, width) = switch (outcome) {
      ScanConfirmed() => (scheme.primary, 4.0),
      ScanRejected() => (scheme.error, 3.0),
      ScanScanning(:final previewValue) when previewValue != null => (
          scheme.tertiary,
          3.0,
        ),
      _ => (Colors.white70, 2.0),
    };

    final preview =
        outcome is ScanScanning ? (outcome as ScanScanning).previewValue : null;

    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final h = constraints.maxHeight;
        return Stack(
          children: [
            Positioned(
              left: roi.left * w,
              top: roi.top * h,
              width: roi.width * w,
              height: roi.height * h,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 120),
                decoration: BoxDecoration(
                  border: Border.all(color: color, width: width),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            if (preview != null)
              Positioned(
                left: 0,
                right: 0,
                top: roi.bottom * h + 12,
                child: Text(
                  preview,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    // 흔들리는 중이라는 신호. 확정값처럼 보이면 안 된다.
                    color: color.withValues(alpha: 0.7),
                    fontSize: 28,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

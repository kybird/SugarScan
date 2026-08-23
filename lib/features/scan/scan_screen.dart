import 'dart:io' show File, Platform;

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;

import '../../domain/models/glucose_unit.dart';
import '../../domain/models/reading_source.dart';
import '../../domain/services/tag_suggester.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../ocr/ocr.dart';
import 'camera_image_adapter.dart';
import 'confirm_sheet.dart';
import 'manual_entry_sheet.dart';
import 'photo_import_sheet.dart';
import 'photo_preprocessor.dart';
import 'scan_entry.dart';

/// 카메라 스캐너 화면.
///
/// 이 화면이 하는 일은 프레임을 [GlucoseScanner] 에 밀어 넣고 돌아온 결과를
/// 그리는 것뿐이다. 글자 보정도, 값 검증도, 프레임 합의도 하지 않는다 —
/// 전부 OCR 모듈 안에서 끝난다.
///
/// 저장 결과를 [ScanEntry] 로 pop 한다. 영속화는 W8 에서 붙는다.
class ScanScreen extends StatefulWidget {
  /// 테스트에서 실제 부트스트랩 대신 다른 스캐너를 끼우는 구멍.
  /// 지정하지 않으면 [buildGlucoseScanner] 로 만든다.
  const ScanScreen({super.key, GlucoseScanner? scanner})
      : _injectedScanner = scanner;

  final GlucoseScanner? _injectedScanner;

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> with WidgetsBindingObserver {
  /// 카메라 준비를 기다리는 한도.
  ///
  /// 드물게 카메라 서비스가 응답하지 않는 기기가 있다. 무한정 기다리면
  /// 사용자는 도는 표시기만 보게 되므로, 끊고 수동 입력으로 안내한다.
  static const Duration _setupTimeout = Duration(seconds: 6);

  late final GlucoseScanner _scanner =
      widget._injectedScanner ?? buildGlucoseScanner();

  /// 사진 불러오기 경로가 [GlucoseScanner.start] 을 이미 불렀는지.
  /// 카메라가 없는 데스크톱에서는 `_boot` 의 start 호출이 일어나지 않는다.
  bool _scannerStarted = false;

  /// 사진 불러오기로 싣은 이미지. null 이면 카메라 모드다.
  File? _importedPhoto;

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
    // 세로로 고정한다. ROI 계산과 프레임 회전(`uprightRotationFor`)이 세로를
    // 전제하고 있어서, 가로로 돌리면 가이드 박스와 실제 판독 영역이 조용히
    // 어긋난다 — 값이 틀리게 읽히는 쪽이라 그냥 막는다.
    SystemChrome.setPreferredOrientations(const [
      DeviceOrientation.portraitUp,
    ]);
    // 첫 프레임 이후로 미룬다. initState 시점에는 Localizations 같은 상속
    // 위젯을 읽을 수 없다.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _boot();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    // 스캔 화면을 벗어나면 회전 제한을 푼다. 앱 전체를 세로로 묶을 이유는 없다.
    SystemChrome.setPreferredOrientations(DeviceOrientation.values);
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
      _scannerStarted = true;

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
    await _resumeScanning();
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

    await _resumeScanning();
  }

  /// 스캔을 처음부터 다시 시작한다. 시트 취소 후 공통 경로.
  Future<void> _resumeScanning() async {
    _scanner.reset();
    _paused = false;
    _importedPhoto = null;
    if (mounted) setState(() => _outcome = _scanner.lastOutcome);
    await _startStream();
  }

  /// 사진 불러오기 — debug 빌드 전용.
  ///
  /// 합성 데이터 생성기가 만든 장면 이미지 등 정적 사진을 카메라 프레임과
  /// 같은 경로로 넘긴다. 카메라가 없는 Windows 데스크톱에서 판독 경로 전체를
  /// 직접 확인하려는 목적이라 release 에는 없다.
  Future<void> _importPhoto() async {
    _paused = true;
    await _stopStream();
    if (!mounted) return;

    final file = await showPhotoImportSheet(context);
    if (!mounted) return;
    if (file == null) {
      await _resumeScanning();
      return;
    }

    try {
      final bytes = file.readAsBytesSync();
      // 정렬 전처리 — 표시를 찾아 기울기를 펴고 엔진 셀 규격으로 다시
      // 그린다. 엔진은 프레임 전체가 4셀 표시라고 가정하므로 임의 사진은
      // 이 정렬을 거쳐야 읽힌다. 실패(예: 표시가 안 보이는 사진)하면
      // 원본 프레임으로 넘어간다.
      var frame = preprocessPhotoForEngine(bytes);
      if (frame == null) {
        final decoded = img.decodeImage(bytes);
        if (decoded == null) {
          await _resumeScanning();
          return;
        }
        frame = OcrFrame(
          bytes: bytes,
          format: OcrImageFormat.png,
          width: decoded.width,
          height: decoded.height,
        );
      }
      if (!await _ensureScannerStarted()) return;

      // 사진은 정적 이미지라 프레임이 한 종류다. 프레임 합의(기본 3연속)를
      // 같은 프레임 반복으로 채운다 — 카메라와 동일한 확정 조건을 지나게
      // 하기 위해서다.
      setState(() => _importedPhoto = file);
      for (var i = 0; i < 3; i++) {
        final outcome = await _scanner.offer(frame);
        if (!mounted) return;
        setState(() => _outcome = outcome);
        if (outcome is ScanConfirmed) {
          await _handleConfirmed(outcome);
          return;
        }
      }
      // 합의에 못 미쳤으면 사진 모드로 머문다. 상태 텍스트가 판독 상태를
      // 알리고, 새 사진을 고르거나 직접 입력으로 갈 수 있다.
    } on Object {
      if (mounted) {
        await _resumeScanning();
      }
    }
  }

  /// 사진 경로에서 필요할 때 스캐너를 켠다.
  Future<bool> _ensureScannerStarted() async {
    if (_scannerStarted) return true;
    final outcome = await _scanner.start(unit: _unit);
    if (!mounted) return false;
    if (outcome is ScanUnavailable) {
      setState(() => _outcome = outcome);
      return false;
    }
    _scannerStarted = true;
    return true;
  }

  Future<void> _teardown() async {
    await _stopStream();
    await _controller?.dispose();
    _controller = null;
    _scannerStarted = false;
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
          if (_blockedMessage == null || _importedPhoto != null) _buildPreview(),
          _buildFooter(l10n),
        ],
      ),
    );
  }

  Widget _buildPreview() {
    final photo = _importedPhoto;
    if (photo != null) {
      // 사진 모드 — 가이드 박스가 없다. 판독은 프레임 전체(ROI 없음)로
      // 일어났으므로 잘라 보이면 어디를 봤는지와 어긋난다.
      return Image.file(photo, fit: BoxFit.contain);
    }

    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    // 프리뷰와 가이드 박스를 같은 상자 안에 겹쳐 그려야 화면의 사각형과
    // 프레임의 ROI 가 같은 영역을 가리킨다.
    //
    // 다만 센서 종횡비와 회전 보정 때문에 완전히 일치한다고 단정할 수 없다.
    // 실기기에서 눈으로 맞춰 보정해야 하는 부분이다(W2 잔여 과제).
    // `controller.value.aspectRatio` 는 **센서(가로) 기준** 값이다. 16:9 카메라면
    // 1.78 을 돌려주는데, 세로 화면에서 이 값을 그대로 쓰면 "폭이 높이의 1.78배"
    // 인 가로 상자가 만들어지고 그 안에서 텍스처가 눌린다. 뒤집어야 한다.
    //
    // 프리뷰를 화면 가득 채우지(cover) 않는 것은 의도다. 잘라내는 순간 화면의
    // 가이드 박스와 프레임의 ROI 가 가리키는 영역이 어긋나고, 그 어긋남은
    // "인식이 그냥 잘 안 된다"로만 보여서 찾기가 매우 어렵다. 위아래 검은 띠를
    // 감수하고 정렬을 1:1 로 유지한다.
    return Center(
      child: AspectRatio(
        aspectRatio: 1 / controller.value.aspectRatio,
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
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _openManualEntry,
                      icon: const Icon(Icons.keyboard),
                      label: Text(l10n.manualEntryCta),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: const BorderSide(color: Colors.white54),
                        minimumSize: const Size(0, 48),
                      ),
                    ),
                  ),
                  // 사진 불러오기는 판독 경로를 직접 확인하려는 개발용
                  // 구멍이라 debug 빌드에만 노출한다.
                  if (kDebugMode) ...[
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _importPhoto,
                        icon: const Icon(Icons.image),
                        label: Text(l10n.scanImportPhotoCta),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.white,
                          side: const BorderSide(color: Colors.white54),
                          minimumSize: const Size(0, 48),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _statusText(AppLocalizations l10n) {
    // 사진 모드에서는 판독 결과가 곧 상태다. 카메라가 없다는 안내가
    // 결과를 가리면 안 된다.
    if (_blockedMessage != null && _importedPhoto == null) {
      return _blockedMessage!;
    }

    return switch (_outcome) {
      ScanRejected(:final reason) => switch (reason) {
          ScanRejectionReason.meterHigh => l10n.meterShowsHigh,
          ScanRejectionReason.meterLow => l10n.meterShowsLow,
        },
      ScanUnavailable() => l10n.scanUnavailable,
      ScanScanning(:final previewValue) when previewValue != null =>
        l10n.scanReading,
      // 사진 모드에는 가이드 박스가 없다 — 카메라용 안내가 새어 나가면
      // 사용자는 맞춰야 할 가이드를 찾게 된다. 사진용 안내로 바꾼다.
      _ => _importedPhoto == null
          ? l10n.scanGuideHint
          : l10n.scanImportNoReading,
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

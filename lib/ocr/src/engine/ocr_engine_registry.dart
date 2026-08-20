import 'ocr_engine.dart';

class OcrEngineRegistrationError extends Error {
  OcrEngineRegistrationError(this.message);
  final String message;

  @override
  String toString() => 'OcrEngineRegistrationError: $message';
}

/// 등록된 엔진을 런타임에 교체한다.
///
/// 모듈 내부 부품이다. 앱은 이 레지스트리를 만지지 않고 [GlucoseScanner] 만 쓴다.
///
/// 존재 이유는 두 가지다.
/// 1. 개발 중에 같은 화면을 여러 엔진으로 스캔해 A/B 비교할 수 있어야 한다.
/// 2. fine-tune 이 목표 정확도에 못 미쳤을 때 다른 엔진으로 갈아타는 비용이
///    `OcrEngine` 구현 하나 추가로 끝나야 한다.
class OcrEngineRegistry {
  OcrEngineRegistry();

  final Map<String, OcrEngine Function()> _factories = {};
  final Map<String, OcrEngineDescriptor> _descriptors = {};

  OcrEngine? _active;
  String? _activeId;

  String? get activeId => _activeId;
  OcrEngine? get active => _active;
  bool get isEmpty => _factories.isEmpty;

  List<OcrEngineDescriptor> get available =>
      List.unmodifiable(_descriptors.values);

  void register(OcrEngineDescriptor descriptor, OcrEngine Function() factory) {
    // OCR 은 단말에서만 돌아간다. 조건부 허용을 두지 않는 이유는, 플래그가
    // 있으면 언젠가 누군가 그 플래그를 켜기 때문이다.
    if (descriptor.requiresNetwork) {
      throw OcrEngineRegistrationError(
        '엔진 "${descriptor.id}" 은(는) 네트워크를 요구합니다. '
        'OCR 은 온디바이스에서만 동작합니다.',
      );
    }
    if (_factories.containsKey(descriptor.id)) {
      throw OcrEngineRegistrationError('엔진 id 중복: ${descriptor.id}');
    }
    _factories[descriptor.id] = factory;
    _descriptors[descriptor.id] = descriptor;
  }

  bool isRegistered(String id) => _factories.containsKey(id);

  /// 엔진을 활성화한다. 기존 엔진은 반드시 dispose 한 뒤 교체한다
  /// (ONNX 세션·ML Kit 인스턴스가 남으면 메모리를 계속 잡는다).
  Future<OcrEngine> activate(String id, {OcrEngineConfig? config}) async {
    final factory = _factories[id];
    if (factory == null) {
      throw OcrEngineRegistrationError('등록되지 않은 엔진: $id');
    }
    if (_activeId == id && _active != null) return _active!;

    await _active?.dispose();
    _active = null;
    _activeId = null;

    final engine = factory();
    await engine.initialize(config ?? const OcrEngineConfig());
    _active = engine;
    _activeId = id;
    return engine;
  }

  /// 등록된 첫 엔진을 활성화한다. 기본 엔진 선택 로직의 진입점.
  Future<OcrEngine?> activateFirst({OcrEngineConfig? config}) =>
      activateFirstWhere((_) => true, config: config);

  /// 조건을 만족하는 첫 엔진을 활성화한다.
  ///
  /// 엔진마다 읽을 수 있는 단위가 다르므로(소수점 클래스가 없는 모델은 mmol/L
  /// 을 못 읽는다) 사용자의 표시 단위로 후보를 좁히는 데 쓴다.
  Future<OcrEngine?> activateFirstWhere(
    bool Function(OcrEngineDescriptor descriptor) test, {
    OcrEngineConfig? config,
  }) async {
    for (final entry in _descriptors.entries) {
      if (test(entry.value)) {
        return activate(entry.key, config: config);
      }
    }
    return null;
  }

  Future<void> deactivate() async {
    await _active?.dispose();
    _active = null;
    _activeId = null;
  }
}

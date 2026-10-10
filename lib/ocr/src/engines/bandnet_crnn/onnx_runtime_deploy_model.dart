import 'dart:typed_data';

import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';

import 'deploy_model.dart';

/// [DeployOnnxModel] 의 flutter_onnxruntime 구현.
///
/// 입출력 이름·형태는 변환 스크립트(export_deploy_onnx.py)가 ONNX 에 박은
/// 값과 계약으로 맞춘다. getInputInfo 가 iOS/macOS 에 없어 로드 시점 형태
/// 검증은 하지 않고, 첫 run 의 결과 길이로 검증한다(엔진 쪽).
class OnnxRuntimeModel implements DeployOnnxModel {
  OnnxRuntimeModel._(
    this._session,
    this._inputName,
    this._inputShape,
  );

  final OrtSession _session;
  final String _inputName;
  final List<int> _inputShape;

  /// 에셋에서 모델을 불러온다. 없거나 깨졌으면 **null** — 예외를 던지지
  /// 않는 이유는 sevenseg 쪽(TfliteDigitClassifier.tryLoad) 과 같다.
  /// 모델이 없는 빌드에서도 앱은 정상적으로 떠야 한다.
  static Future<OnnxRuntimeModel?> tryLoad(
    String assetPath, {
    required String inputName,
    required List<int> inputShape,
  }) async {
    try {
      final session = await OnnxRuntime().createSessionFromAsset(assetPath);
      return OnnxRuntimeModel._(session, inputName, inputShape);
    } on Object {
      return null;
    }
  }

  @override
  Future<Map<String, Float32List>> run(Float32List input) async {
    final inputOrt = await OrtValue.fromList(input, _inputShape);
    try {
      final outputs = await _session.run({_inputName: inputOrt});
      try {
        final result = <String, Float32List>{};
        for (final entry in outputs.entries) {
          final flat = await entry.value.asFlattenedList();
          result[entry.key] = Float32List.fromList(
            [for (final v in flat) (v as num).toDouble()],
          );
        }
        return result;
      } finally {
        for (final value in outputs.values) {
          await value.dispose();
        }
      }
    } finally {
      await inputOrt.dispose();
    }
  }

  @override
  Future<void> dispose() => _session.close();
}

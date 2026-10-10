import 'dart:typed_data';

/// 배포 모델 ONNX 세션의 최소 계약.
///
/// 엔진과 테스트는 이 인터페이스만 안다. flutter_onnxruntime import 는
/// 구현 파일(`onnx_runtime_deploy_model.dart`) 한 곳에 격리되어 있어,
/// 엔진 유닛테스트는 Flutter 런타임 없이 가짜 세션으로 돈다.
abstract class DeployOnnxModel {
  /// [input] 을 모델 입력에 넣고 출력 텐서들을 이름별 1차원 배열로 돌려준다.
  ///
  /// 구현은 자원을 스스로 회수해야 한다(입·출력 OrtValue dispose).
  Future<Map<String, Float32List>> run(Float32List input);

  Future<void> dispose();
}

import 'package:camera/camera.dart';

import '../../ocr/ocr.dart';
import 'camera_frame_converter.dart';

/// 카메라 플러그인 타입과 OCR 모듈 사이의 유일한 접합점.
///
/// 이 파일만 `package:camera` 를 안다. 프레임을 실제로 주무르는 계산은
/// [CameraFrameConverter] 에 있고, 그쪽은 플러그인 없이 테스트된다.
OcrFrame? ocrFrameFromCameraImage(
  CameraImage image, {
  required int rotationDegrees,
  NormalizedRect? roi,
}) {
  if (image.planes.isEmpty) return null;
  final plane = image.planes.first;
  final bytesPerRow = plane.bytesPerRow;

  return switch (image.format.group) {
    // Android. UV 평면은 읽지 않는다 — Y 평면이 곧 우리가 필요한 휘도다.
    ImageFormatGroup.yuv420 || ImageFormatGroup.nv21 =>
      CameraFrameConverter.fromLumaPlane(
        plane: plane.bytes,
        width: image.width,
        height: image.height,
        bytesPerRow: bytesPerRow,
        rotationDegrees: rotationDegrees,
        roi: roi,
      ),

    // iOS.
    ImageFormatGroup.bgra8888 => CameraFrameConverter.fromBgra8888(
        plane: plane.bytes,
        width: image.width,
        height: image.height,
        bytesPerRow: bytesPerRow,
        rotationDegrees: rotationDegrees,
        roi: roi,
      ),

    _ => null,
  };
}

/// 센서 방향과 기기 방향으로부터 프레임을 세울 각도를 구한다.
///
/// 스캔 화면은 세로로 고정되어 있으므로 센서 방향만 보정하면 된다. 화면 회전을
/// 허용하게 되면 여기에 기기 방향을 더해야 한다.
int uprightRotationFor(CameraDescription camera) {
  return switch (camera.lensDirection) {
    // 전면 카메라는 좌우가 뒤집혀 들어오지만, 혈당계 스캔은 후면 카메라만
    // 쓰므로 여기서는 보정하지 않는다.
    CameraLensDirection.front => (360 - camera.sensorOrientation) % 360,
    _ => camera.sensorOrientation % 360,
  };
}

import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../ocr/ocr.dart';

/// [OcrCrop](grayscale8) 를 화면에 그리는 위젯.
///
/// 라이브 미리보기에서는 매 프레임 갱신되므로 PNG 왕복 없이 픽셀을 곧장
/// 이미지로 만든다. 디코드는 비동기라 한 프레임 늦게 반영될 수 있고, 실패하면
/// 아무것도 그리지 않는다 — 표시 부속물이 스캔 흐름을 방해해서는 안 된다.
class OcrCropImage extends StatefulWidget {
  const OcrCropImage({
    super.key,
    required this.crop,
    this.maxHeight = 56,
    this.filterQuality = FilterQuality.none,
  });

  final OcrCrop crop;

  /// 표시 높이 상한. 원본 비율은 유지된다.
  final double maxHeight;

  /// 세그먼트 계단현상을 그대로 보여야 하므로 기본은 nearest.
  final FilterQuality filterQuality;

  @override
  State<OcrCropImage> createState() => _OcrCropImageState();
}

class _OcrCropImageState extends State<OcrCropImage> {
  ui.Image? _image;

  @override
  void initState() {
    super.initState();
    _decode();
  }

  @override
  void didUpdateWidget(covariant OcrCropImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    // 엔진은 프레임마다 새 크롭을 내놓는다. 참조가 같으면 다시 디코드하지
    // 않는다 — 스캐너가 드롭된 프레임에 대해 직전 결과를 되돌릴 때 불필요한
    // 디코드가 매번 일어나는 것을 막는다.
    if (!identical(oldWidget.crop, widget.crop)) _decode();
  }

  Future<void> _decode() async {
    final crop = widget.crop;
    // 치수와 바이트 길이가 어긋난 크롭은 그리지 않는다. 망가진 부속물을
    // 세워고 치는 것보다 숨기는 편이 스캔 화면에 해가 없다.
    if (crop.bytes.length < crop.width * crop.height) {
      if (mounted) setState(() => _image = null);
      return;
    }
    try {
      // r8 픽셀 포맷은 엔진 API 에 없다 — grayscale8 을 RGBA 로 펴서 넣는다.
      // 크롭이 작아(숫자 띠 몇 줌) 펴는 비용은 매 프레임이어도 감당한다.
      final rgba = Uint8List(crop.width * crop.height * 4);
      var o = 0;
      for (final b in crop.bytes) {
        rgba[o++] = b;
        rgba[o++] = b;
        rgba[o++] = b;
        rgba[o++] = 255;
      }
      final buffer = await ui.ImmutableBuffer.fromUint8List(rgba);
      final descriptor = ui.ImageDescriptor.raw(
        buffer,
        width: crop.width,
        height: crop.height,
        pixelFormat: ui.PixelFormat.rgba8888,
      );
      final codec = await descriptor.instantiateCodec();
      final frame = await codec.getNextFrame();
      codec.dispose();
      descriptor.dispose();
      // 대기 사이 크롭이 바뀌었을 수 있다. 늦은 결과로 새 크롭을 덮지 않는다.
      if (!mounted || !identical(widget.crop, crop)) {
        frame.image.dispose();
        return;
      }
      final replaced = _image;
      setState(() => _image = frame.image);
      // 라이브 스캔에서는 프레임마다 새 이미지가 만들어진다. 쓰던 것을
      // 놓지 않으면 GPU 메모리가 계속 자란다. 단, 이번 프레임이 그리기를
      // 마친 뒤에 폐기해야 그리는 중인 이미지가 사라지지 않는다.
      if (replaced != null) {
        WidgetsBinding.instance.addPostFrameCallback((_) => replaced.dispose());
      }
    } on Object {
      if (mounted && identical(widget.crop, crop)) {
        setState(() => _image = null);
      }
    }
  }

  @override
  void dispose() {
    _image?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final image = _image;
    if (image == null) return const SizedBox.shrink();
    return SizedBox(
      height: widget.maxHeight,
      child: FittedBox(
        fit: BoxFit.scaleDown,
        child: RawImage(
          image: image,
          filterQuality: widget.filterQuality,
        ),
      ),
    );
  }
}

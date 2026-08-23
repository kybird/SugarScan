import 'dart:io';

import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';

/// 사진 불러오기 시트 — 개발 전용.
///
/// 카메라가 없는 Windows 데스크톱이나 에뮬레이터에서도 실제 판독 경로를
/// 돌려 보게 하는 구멍이다. 합성 데이터 생성기(`tools/synth7seg`)가 만든
/// 장면 이미지를 골라 담으면 카메라 프레임과 같은 경로(`GlucoseScanner.offer`)
/// 를 지나 확인 시트까지 간다. 이 시트로 가는 버튼은 debug 빌드에만 있다.
Future<File?> showPhotoImportSheet(
  BuildContext context, {
  String initialDirectory = defaultSynthImageDirectory,
}) {
  return showModalBottomSheet<File?>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => _PhotoImportSheet(initialDirectory: initialDirectory),
  );
}

/// 합성 데이터 생성기의 기본 출력 경로.
///
/// 데스크톱 debug 실행은 저장소 루트에서 일어나므로 상대 경로가 그대로
/// 닿는다. 다른 폴더를 보려면 시트의 경로 칸을 고치면 된다.
const String defaultSynthImageDirectory = 'assets_dev/synth/images';

class _PhotoImportSheet extends StatefulWidget {
  const _PhotoImportSheet({required this.initialDirectory});

  final String initialDirectory;

  @override
  State<_PhotoImportSheet> createState() => _PhotoImportSheetState();
}

class _PhotoImportSheetState extends State<_PhotoImportSheet> {
  late final TextEditingController _pathController;
  List<File> _files = const [];
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _pathController = TextEditingController(text: widget.initialDirectory);
    _refresh();
  }

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  void _refresh() {
    try {
      final files = Directory(_pathController.text)
          .listSync()
          .whereType<File>()
          .where((f) => f.path.toLowerCase().endsWith('.png'))
          .toList()
        ..sort((a, b) => a.path.compareTo(b.path));
      setState(() {
        _files = files;
        _failed = false;
      });
    } on Object {
      setState(() {
        _files = const [];
        _failed = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        bottom: 24 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.7,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              l10n.scanImportPickTitle,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _pathController,
                    onSubmitted: (_) => _refresh(),
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
                IconButton(
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (_failed || _files.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 24),
                child: Text(
                  l10n.scanImportNoImages,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              )
            else
              Expanded(
                child: ListView.builder(
                  itemCount: _files.length,
                  itemBuilder: (context, index) {
                    final file = _files[index];
                    final name = file.path.split(RegExp(r'[\\/]')).last;
                    return ListTile(
                      dense: true,
                      title: Text(name),
                      onTap: () => Navigator.of(context).pop(file),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}

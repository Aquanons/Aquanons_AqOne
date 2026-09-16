import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

/// Pan-and-zoom circular cropper for the profile photo.
///
/// Hand-rolled rather than pulled from a package. The two obvious candidates
/// both cost more than they give here: image_cropper needs a UCropActivity in
/// the Android manifest and native config, which is the exact class of thing
/// that broke this build once already, and a pure-Dart package would still be
/// a dependency to keep current for a screen that crops to one fixed shape.
///
/// Returns the cropped image as PNG bytes, or null if the user backs out.
class AvatarCropPage extends StatefulWidget {
  const AvatarCropPage({super.key, required this.source});

  /// The picked file, straight from the camera or gallery.
  final File source;

  /// Edge length of the written image. 512 is comfortably more than the
  /// largest place it is displayed (88px at 3x) without storing a photo the
  /// size of the original on a phone that may be short of space.
  static const int outputSize = 512;

  @override
  State<AvatarCropPage> createState() => _AvatarCropPageState();
}

class _AvatarCropPageState extends State<AvatarCropPage> {
  final TransformationController _controller = TransformationController();
  ui.Image? _image;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _controller.dispose();
    _image?.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final Uint8List bytes = await widget.source.readAsBytes();
      final ui.Codec codec = await ui.instantiateImageCodec(bytes);
      final ui.FrameInfo frame = await codec.getNextFrame();
      if (!mounted) {
        frame.image.dispose();
        return;
      }
      setState(() => _image = frame.image);
    } catch (_) {
      if (mounted) {
        setState(() => _error = AppLocalizations.of(context).cropPhotoError);
      }
    }
  }

  /// Renders the visible circle at [AvatarCropPage.outputSize].
  ///
  /// Re-renders from the decoded original rather than screenshotting the
  /// widget, so the result is as sharp as the source allows instead of being
  /// limited to the on-screen preview size.
  Future<void> _confirm(double viewport) async {
    final ui.Image? image = _image;
    if (image == null || _saving) {
      return;
    }
    setState(() => _saving = true);

    try {
      // InteractiveViewer's matrix maps the child's coordinates onto the
      // viewport. Inverting it turns the visible square back into a rectangle
      // in child space, which is the crop.
      final Matrix4 inverse = Matrix4.inverted(_controller.value);
      final Offset topLeft = MatrixUtils.transformPoint(inverse, Offset.zero);
      final Offset bottomRight =
          MatrixUtils.transformPoint(inverse, Offset(viewport, viewport));

      // The child was laid out as a BoxFit.cover square of side `viewport`,
      // so map child coordinates back onto the source pixels.
      final double scale = image.width > image.height
          ? viewport / image.height
          : viewport / image.width;
      final double coveredW = image.width * scale;
      final double coveredH = image.height * scale;
      final double offsetX = (coveredW - viewport) / 2;
      final double offsetY = (coveredH - viewport) / 2;

      final Rect src = Rect.fromLTRB(
        (topLeft.dx + offsetX) / scale,
        (topLeft.dy + offsetY) / scale,
        (bottomRight.dx + offsetX) / scale,
        (bottomRight.dy + offsetY) / scale,
      ).intersect(
        Rect.fromLTWH(0, 0, image.width.toDouble(), image.height.toDouble()),
      );

      final double side = AvatarCropPage.outputSize.toDouble();
      final ui.PictureRecorder recorder = ui.PictureRecorder();
      final Canvas canvas = Canvas(recorder);
      // Opaque backing: a transparent corner would show through as black on
      // some Android image viewers if the photo is ever shared out.
      canvas.drawRect(
        Rect.fromLTWH(0, 0, side, side),
        Paint()..color = const Color(0xFF0F172A),
      );
      canvas.drawImageRect(
        image,
        src,
        Rect.fromLTWH(0, 0, side, side),
        Paint()..filterQuality = FilterQuality.high,
      );
      final ui.Image out = await recorder
          .endRecording()
          .toImage(AvatarCropPage.outputSize, AvatarCropPage.outputSize);
      final ByteData? png = await out.toByteData(
        format: ui.ImageByteFormat.png,
      );
      out.dispose();

      if (!mounted) {
        return;
      }
      if (png == null) {
        setState(() {
          _saving = false;
          _error = AppLocalizations.of(context).cropPhotoError;
        });
        return;
      }
      Navigator.of(context).pop<Uint8List>(png.buffer.asUint8List());
    } catch (_) {
      if (mounted) {
        setState(() {
          _saving = false;
          _error = AppLocalizations.of(context).cropPhotoError;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ui.Image? image = _image;

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        foregroundColor: Colors.white,
        title: Text(AppLocalizations.of(context).cropPhotoTitle),
      ),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            // A square viewport, inset so the mask never touches the edges.
            final double viewport = (constraints.maxWidth < constraints.maxHeight
                    ? constraints.maxWidth
                    : constraints.maxHeight) -
                48;

            return Column(
              children: <Widget>[
                const Spacer(),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white70),
                    ),
                  )
                else if (image == null)
                  const CircularProgressIndicator()
                else
                  SizedBox(
                    width: viewport,
                    height: viewport,
                    child: ClipOval(
                      child: InteractiveViewer(
                        transformationController: _controller,
                        minScale: 1,
                        maxScale: 5,
                        // No panning past the edges: the crop maths assumes
                        // the visible square is inside the image.
                        constrained: true,
                        clipBehavior: Clip.none,
                        child: SizedBox(
                          width: viewport,
                          height: viewport,
                          child: RawImage(
                            image: image,
                            fit: BoxFit.cover,
                          ),
                        ),
                      ),
                    ),
                  ),
                const SizedBox(height: 18),
                Text(
                  AppLocalizations.of(context).cropPhotoHint,
                  style: const TextStyle(color: Colors.white54, fontSize: 12.5),
                ),
                const Spacer(),
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                  child: Row(
                    children: <Widget>[
                      Expanded(
                        child: TextButton(
                          onPressed: _saving
                              ? null
                              : () => Navigator.of(context).pop(),
                          style: TextButton.styleFrom(
                            foregroundColor: Colors.white70,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          child: Text(AppLocalizations.of(context).actionCancel),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 2,
                        child: FilledButton(
                          onPressed: image == null || _saving
                              ? null
                              : () => _confirm(viewport),
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFF0F69C9),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          child: _saving
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : Text(AppLocalizations.of(context).cropPhotoUse),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

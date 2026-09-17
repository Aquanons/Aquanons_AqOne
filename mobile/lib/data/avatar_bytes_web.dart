import 'dart:typed_data';

/// The avatar picker is disabled on web (`profile_page.dart` guards on
/// `kIsWeb`), so there is never a file to read here.
Future<Uint8List?> readAvatarBytes(String? path) async => null;

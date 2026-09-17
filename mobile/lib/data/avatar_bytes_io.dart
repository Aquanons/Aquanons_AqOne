import 'dart:io';
import 'dart:typed_data';

/// Reads the cropped profile photo so it can be pushed to the backend.
///
/// Null covers both "no photo" and "the file could not be read" - callers must
/// not treat a transient read failure as an instruction to erase the stored
/// photo. `registerVesselProfile` sends an explicit empty string to clear.
Future<Uint8List?> readAvatarBytes(String? path) async {
  if (path == null || path.isEmpty) {
    return null;
  }
  try {
    final File file = File(path);
    if (!await file.exists()) {
      return null;
    }
    return await file.readAsBytes();
  } catch (_) {
    return null;
  }
}

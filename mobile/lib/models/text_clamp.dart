import 'dart:convert';
import 'package:characters/characters.dart';

/// Clamps [text] to at most [maxBytes] UTF-8 encoded bytes without splitting
/// characters or multi-byte sequences.
String clampUtf8(String text, int maxBytes) {
  if (maxBytes <= 0) {
    return '';
  }
  final bytes = utf8.encode(text);
  if (bytes.length <= maxBytes) {
    return text;
  }

  final buffer = StringBuffer();
  var currentBytes = 0;
  for (final char in text.characters) {
    final charBytes = utf8.encode(char).length;
    if (currentBytes + charBytes > maxBytes) {
      break;
    }
    buffer.write(char);
    currentBytes += charBytes;
  }
  return buffer.toString();
}

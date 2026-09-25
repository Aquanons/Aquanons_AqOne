import 'dart:convert';

import 'package:aqone/models/text_clamp.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('clampUtf8', () {
    test('ASCII is unchanged', () {
      const text = 'Emergency on boat Alpha';
      expect(clampUtf8(text, 64), text);
      expect(clampUtf8(text, 32), text);
    });

    test('ñ at the boundary is dropped whole', () {
      // 'abc' is 3 bytes. 'ñ' is 2 bytes. Total 5 bytes.
      const text = 'abcñ';
      final clamped = clampUtf8(text, 4);
      expect(clamped, 'abc');
      expect(utf8.encode(clamped).length, lessThanOrEqualTo(4));
    });

    test('an emoji at the boundary is dropped whole', () {
      // 'abc' is 3 bytes. '🌊' is 4 bytes. Total 7 bytes.
      const text = 'abc🌊';
      final clamped = clampUtf8(text, 5);
      expect(clamped, 'abc');
      expect(utf8.encode(clamped).length, lessThanOrEqualTo(5));
    });

    test('the result utf8.encode length is at most maxBytes', () {
      const complex = 'Bangka Ni Niño 🚤🌊 - Dagat kan Aklan';
      for (var max = 0; max <= 50; max++) {
        final result = clampUtf8(complex, max);
        expect(utf8.encode(result).length, lessThanOrEqualTo(max));
      }
    });
  });
}

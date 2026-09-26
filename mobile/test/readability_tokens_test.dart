import 'package:aqone/core/tokens.dart';
import 'package:aqone/models/fisher_sos_situation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

// docs/64_FISHER_FRICTION_REDUCTION_SPEC.md P4 and FFR-11: readable in sun.
double _contrast(Color a, Color b) {
  final la = a.computeLuminance();
  final lb = b.computeLuminance();
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

void main() {
  final palettes = <String, AqPalette>{
    'light': AqPalette.light,
    'dark': AqPalette.dark,
  };

  palettes.forEach((name, p) {
    group('$name palette', () {
      final backgrounds = <String, Color>{
        'canvas': p.canvas,
        'surface': p.surface,
      };
      final texts = <String, Color>{
        'primaryText': p.primaryText,
        'secondaryText': p.secondaryText,
        'dimText': p.dimText,
      };

      texts.forEach((textName, text) {
        backgrounds.forEach((bgName, bg) {
          test('$textName on $bgName is at least 4.5:1', () {
            expect(_contrast(text, bg), greaterThanOrEqualTo(4.5),
                reason: '$textName on $bgName');
          });
        });
      });

      test('primaryText on surface is at least 7:1 (SOS status text)', () {
        expect(_contrast(p.primaryText, p.surface), greaterThanOrEqualTo(7));
      });

      for (final situation in FisherSosSituation.values) {
        test('${situation.name} icon colour is at least 3:1 on surface', () {
          expect(_contrast(situation.color, p.surface), greaterThanOrEqualTo(3),
              reason: 'a status icon a fisher cannot see in sun says nothing');
        });
      }
    });
  });
}

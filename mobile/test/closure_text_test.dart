import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/ui/widgets/closure_text.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('closureMessage', () {
    test('rescued, safe_confirmed and stood_down_by_fisher give sosClosedByMdrrmo', () async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      expect(closureMessage(t, 'rescued'), t.sosClosedByMdrrmo);
      expect(closureMessage(t, 'safe_confirmed'), t.sosClosedByMdrrmo);
      expect(closureMessage(t, 'stood_down_by_fisher'), t.sosClosedByMdrrmo);
    });

    test('closed_unconfirmed, unspecified and null give sosClosedUnconfirmed', () async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      expect(closureMessage(t, 'closed_unconfirmed'), t.sosClosedUnconfirmed);
      expect(closureMessage(t, 'unspecified'), t.sosClosedUnconfirmed);
      expect(closureMessage(t, null), t.sosClosedUnconfirmed);
      expect(closureMessage(t, ''), t.sosClosedUnconfirmed);
    });

    test('duplicate gives sosClosedDuplicate', () async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      expect(closureMessage(t, 'duplicate'), t.sosClosedDuplicate);
    });
  });
}

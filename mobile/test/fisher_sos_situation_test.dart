import 'package:aqone/core/tokens.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/delivery_policy.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/fisher_sos_situation.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

// docs/64_FISHER_FRICTION_REDUCTION_SPEC.md Section 2.4, FFR-03.
final DateTime _now = DateTime.utc(2026, 9, 25, 8);
final int _nowSec = _now.millisecondsSinceEpoch ~/ 1000;

SosRecord _rec({
  DeliveryState state = DeliveryState.saved,
  int? relayedAt,
  String? etaAt,
  String? resolvedAt,
  int? fisherReply,
  bool fisherReplySynced = false,
}) {
  return SosRecord(
    localId: 'local-1',
    vesselId: '0123456789abcdef0123456789abcdef',
    boat: 'BG-123',
    clientTs: _nowSec - 60,
    state: state,
    relayedAt: relayedAt,
    etaAt: etaAt,
    resolvedAt: resolvedAt,
    fisherReply: fisherReply,
    fisherReplySynced: fisherReplySynced,
  );
}

FisherSosSituation _of(SosRecord r) => FisherSosSituation.of(r, now: _now);

void main() {
  final eta = _now.add(const Duration(minutes: 30)).toIso8601String();
  final resolved = _now.toIso8601String();
  final recentRelay = _nowSec - 60;
  final staleRelay = _nowSec - podDeliveryDeadline.inSeconds - 1;

  group('FisherSosSituation.of maps one record to one situation', () {
    test('saved is not sent yet', () {
      expect(_of(_rec()), FisherSosSituation.notSentYet);
    });

    test('relayed within the pod deadline: the pod has it', () {
      expect(
        _of(_rec(state: DeliveryState.relayed, relayedAt: recentRelay)),
        FisherSosSituation.podHasIt,
      );
    });

    test('relayed past the pod deadline: pod has it, shore not confirmed', () {
      expect(
        _of(_rec(state: DeliveryState.relayed, relayedAt: staleRelay)),
        FisherSosSituation.podNotConfirmed,
      );
    });

    test('delivered: the rescue centre has it', () {
      expect(
        _of(_rec(state: DeliveryState.delivered)),
        FisherSosSituation.rescueCentreHasIt,
      );
    });

    test('acknowledged: help is coming', () {
      expect(
        _of(_rec(state: DeliveryState.acknowledged)),
        FisherSosSituation.helpComing,
      );
    });

    test(
        'a responder ETA is acknowledgement evidence even before the state catches up',
        () {
      expect(
        _of(_rec(state: DeliveryState.delivered, etaAt: eta)),
        FisherSosSituation.helpComing,
      );
    });

    test('still-in-danger reply keeps the delivery situation', () {
      expect(
        _of(_rec(state: DeliveryState.delivered, fisherReply: 1)),
        FisherSosSituation.rescueCentreHasIt,
      );
    });

    test('safe-now reply not yet confirmed by the backend: cancelling', () {
      for (final state in DeliveryState.values) {
        expect(
          _of(_rec(state: state, fisherReply: 2)),
          FisherSosSituation.cancelling,
          reason: '$state',
        );
      }
    });

    test('safe-now reply confirmed by the backend: cancelled', () {
      for (final state in DeliveryState.values) {
        expect(
          _of(_rec(state: state, fisherReply: 2, fisherReplySynced: true)),
          FisherSosSituation.cancelled,
          reason: '$state',
        );
      }
    });

    test('resolution by the rescue centre wins over everything else', () {
      for (final state in DeliveryState.values) {
        for (final reply in <int?>[null, 1, 2]) {
          for (final synced in <bool>[false, true]) {
            expect(
              _of(_rec(
                state: state,
                etaAt: eta,
                resolvedAt: resolved,
                fisherReply: reply,
                fisherReplySynced: synced,
              )),
              FisherSosSituation.closed,
              reason: '$state reply=$reply synced=$synced',
            );
          }
        }
      }
    });
  });

  group('honesty (docs/06): nothing looks later than its evidence', () {
    const notYetAtShore = <FisherSosSituation>{
      FisherSosSituation.notSentYet,
      FisherSosSituation.podHasIt,
      FisherSosSituation.podNotConfirmed,
    };

    test('saved and relayed never map to a shore-confirmed situation', () {
      for (final state in <DeliveryState>[
        DeliveryState.saved,
        DeliveryState.relayed,
      ]) {
        for (final relayedAt in <int?>[null, recentRelay, staleRelay]) {
          final situation = _of(_rec(state: state, relayedAt: relayedAt));
          expect(notYetAtShore, contains(situation), reason: '$state');
        }
      }
    });

    test('situations before shore never use the success colour or a check mark',
        () {
      final checkIcons = <IconData>{
        Icons.check_circle_rounded,
        Icons.check_circle,
        Icons.check_circle_outline,
        Icons.check_rounded,
        Icons.task_alt_rounded,
        Icons.cloud_done_rounded,
      };
      for (final situation in notYetAtShore) {
        expect(situation.color, isNot(AqColors.success), reason: '$situation');
        expect(checkIcons, isNot(contains(situation.icon)),
            reason: '$situation');
      }
    });

    test('every situation has its own icon', () {
      final icons = FisherSosSituation.values.map((s) => s.icon).toSet();
      expect(icons.length, FisherSosSituation.values.length);
    });
  });

  group('FisherSosSituationL10n', () {
    for (final code in <String>['en', 'fil', 'akl']) {
      test(
          '$code: every situation has a non-empty, distinct title and description',
          () async {
        final t = await AppLocalizations.delegate.load(Locale(code));
        final titles = <String>{};
        final descriptions = <String>{};
        for (final situation in FisherSosSituation.values) {
          final title = situation.title(t);
          final description = situation.description(t);
          expect(title.trim(), isNotEmpty, reason: '$situation');
          expect(description.trim(), isNotEmpty, reason: '$situation');
          titles.add(title);
          descriptions.add(description);
        }
        expect(descriptions.length, FisherSosSituation.values.length);
        // podHasIt and podNotConfirmed may share a title ("the pod has it");
        // everything else must read differently.
        expect(titles.length,
            greaterThanOrEqualTo(FisherSosSituation.values.length - 1));
      });
    }
  });
}

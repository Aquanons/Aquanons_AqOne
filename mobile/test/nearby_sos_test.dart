import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/nearby_sos.dart';
import 'package:aqone/services/nearby_alarm.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('parses nearby broadcasts nearest-first and skips rows without position', () {
    final items = NearbySos.parseList({
      'broadcasts': [
        {
          'broadcast_id': 2,
          'sos_event_id': 20,
          'center_lat': 11.71,
          'center_lon': 122.45,
          'distance_km': 5.0,
        },
        {
          'broadcast_id': 1,
          'sos_event_id': 10,
          'center_lat': 11.70,
          'center_lon': 122.44,
          'distance_km': 0.45,
          'eta_at': '2026-09-30T10:42:00+00:00',
          'responder_status': 2,
        },
        {'broadcast_id': 3, 'sos_event_id': 30},
      ],
    });
    expect(items.length, 2);
    expect(items.first.broadcastId, 1);
    expect(items.first.etaAt, isNotNull);
    expect(items.first.responderStatus, 2);
  });

  // docs/73 Rev 2 G9: the distance is localized and "away" appears once.
  test('distance text is localized, metres below 1 km, and says away once', () async {
    final en = await AppLocalizations.delegate.load(const Locale('en'));
    expect(NearbySos.distanceText(0.45, en), '450 m');
    expect(NearbySos.distanceText(2.34, en), '2.3 km');
    expect(NearbySos.distanceText(null, en), en.nearbyHelpDistanceUnknown);
    expect(en.nearbyHelpAway(NearbySos.distanceText(2.34, en)), '2.3 km away');

    final akl = await AppLocalizations.delegate.load(const Locale('akl'));
    expect(akl.nearbyHelpAway(NearbySos.distanceText(2.34, akl)), isNot(contains('away')));
    expect(NearbySos.distanceText(null, akl), akl.nearbyHelpDistanceUnknown);
  });

  // docs/64 P6: the fisher's core path never names the MDRRMO.
  test('the nearby-help notification never says MDRRMO', () async {
    for (final code in <String>['en', 'fil', 'akl']) {
      final t = await AppLocalizations.delegate.load(Locale(code));
      expect(t.nearbyHelpNotifBody('2.3 km'), isNot(contains('MDRRMO')), reason: code);
      expect(t.nearbyHelpNotifTitle, isNot(contains('MDRRMO')), reason: code);
    }
  });

  test('nearby alarm uses broadcastalarm.mp3 with alarm usage', () {
    expect(NearbyAlarm.asset, 'audio/broadcastalarm.mp3');
    expect(NearbyAlarm.alarmContext.android.usageType, AndroidUsageType.alarm);
    expect(NearbyAlarm.alarmContext.android.contentType, AndroidContentType.sonification);
  });
}

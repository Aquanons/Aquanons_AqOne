import 'package:aqone/models/nearby_sos.dart';
import 'package:aqone/services/nearby_alarm.dart';
import 'package:audioplayers/audioplayers.dart';
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

  test('distance text uses meters below 1 km and unknown when null', () {
    expect(NearbySos.distanceText(0.45), '450 m away');
    expect(NearbySos.distanceText(2.34), '2.3 km away');
    expect(NearbySos.distanceText(null), 'distance unknown');
  });

  test('nearby alarm uses broadcastalarm.mp3 with alarm usage', () {
    expect(NearbyAlarm.asset, 'audio/broadcastalarm.mp3');
    expect(NearbyAlarm.alarmContext.android.usageType, AndroidUsageType.alarm);
    expect(NearbyAlarm.alarmContext.android.contentType, AndroidContentType.sonification);
  });
}

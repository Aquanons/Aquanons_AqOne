// docs/73 Rev 2 G10: tapping the nearby-help notification opens At sea at
// that broadcast. Acceptance tests written by the spec author; do not edit
// them to make them pass. The real tap still needs the device check in
// docs/reconciliation/HANDOFF-gemini-2026-09-30.md.

import 'package:aqone/services/eta_notifier.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('the nearby payload round-trips a broadcast id and nothing else', () {
    expect(EtaNotifier.nearbyPayload(7), 'nearby:7');
    expect(EtaNotifier.broadcastIdFromPayload('nearby:7'), 7);
    expect(EtaNotifier.broadcastIdFromPayload('nearby:x'), isNull);
    expect(EtaNotifier.broadcastIdFromPayload('rescue_eta'), isNull);
    expect(EtaNotifier.broadcastIdFromPayload(null), isNull);
  });

  test('a tapped nearby notification is published to nearbyTaps', () async {
    final taps = <int>[];
    final sub = EtaNotifier.nearbyTaps.listen(taps.add);

    EtaNotifier.handleNotificationPayload('nearby:9');
    EtaNotifier.handleNotificationPayload('rescue_eta');
    EtaNotifier.handleNotificationPayload(null);
    await Future<void>.delayed(Duration.zero);

    expect(taps, <int>[9]);
    await sub.cancel();
  });
}

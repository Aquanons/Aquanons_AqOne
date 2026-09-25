import 'package:aqone/models/squall_watch.dart';
import 'package:aqone/services/sos_alarm.dart';
import 'package:aqone/services/squall_alarm.dart';
import 'package:flutter_test/flutter_test.dart';

class _CountingAlarm implements SosAlarm {
  int starts = 0;
  bool _ringing = false;

  @override
  bool get isRinging => _ringing;

  @override
  Future<void> start() async {
    starts++;
    _ringing = true;
  }

  @override
  Future<void> stop() async {
    _ringing = false;
  }

  @override
  Future<void> dispose() async {}
}

SquallWatch _returnNow(DateTime observedAt) => SquallWatch.tryParse({
      'level': 'return_now',
      'return_now': true,
      'triggered_buoys': ['B01', 'B02'],
      'observed_at': observedAt.toIso8601String(),
    })!;

void main() {
  test('[mobile.squall.ack-survives-missed-clear] a squall six hours later on '
      'the same buoys alarms again after a missed clear', () {
    final fake = _CountingAlarm();
    final alarm = SquallAlarm(alarm: fake);
    final first = _returnNow(DateTime.utc(2026, 9, 1, 6));
    final second = _returnNow(DateTime.utc(2026, 9, 1, 12));

    alarm.start(first.identity);
    alarm.acknowledge();
    // The "clear" poll between the two squalls was missed (no signal), so
    // AppShell never calls alarm.clear().
    alarm.start(second.identity);

    expect(
      fake.starts,
      2,
      reason: 'the second squall reuses identity "${second.identity}", so the '
          'earlier acknowledgement silences it',
    );
  });
}

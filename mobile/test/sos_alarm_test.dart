import 'package:audioplayers/audioplayers.dart';
import 'package:aqone/services/sos_alarm.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // Reads the static context rather than building a SosAlarm: a real
  // AudioPlayer's async platform create fails in the test host and the
  // unhandled error lands on whichever test is running at the time.
  test('the alarm player is configured with AndroidUsageType.alarm and AndroidContentType.sonification', () {
    expect(SosAlarm.alarmContext.android.usageType, AndroidUsageType.alarm);
    expect(SosAlarm.alarmContext.android.contentType, AndroidContentType.sonification);
  });
}

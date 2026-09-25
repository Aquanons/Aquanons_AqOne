import 'package:audioplayers/audioplayers.dart';
import 'package:aqone/services/sos_alarm.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('the alarm player is configured with AndroidUsageType.alarm and AndroidContentType.sonification', () {
    final alarm = SosAlarm();
    expect(alarm.audioContext.android.usageType, AndroidUsageType.alarm);
    expect(alarm.audioContext.android.contentType, AndroidContentType.sonification);
  });
}

import 'package:aqone/ui/home_page.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('stripSsidQuotes unwraps Android-quoted names and blanks unknowns', () {
    expect(stripSsidQuotes('"AqOne-Buoy-01"'), 'AqOne-Buoy-01');
    expect(stripSsidQuotes('AqOne-Buoy-01'), 'AqOne-Buoy-01');
    expect(stripSsidQuotes('<unknown ssid>'), isEmpty);
    expect(stripSsidQuotes(null), isEmpty);
    expect(stripSsidQuotes(''), isEmpty);
  });
}

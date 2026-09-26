import 'package:aqone/data/map_snapshot_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/ui/widgets/offline_map_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget wrap(Map<String, DateTime> ages) {
    return MaterialApp(
      locale: const Locale('en'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(body: OfflineMapBanner(ages: ages, isDark: false)),
    );
  }

  DateTime ago(Duration d) => DateTime.now().subtract(d);

  testWidgets('stays out of the way when the map is live', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      wrap(<String, DateTime>{
        MapSnapshotStore.feedBuoys: ago(const Duration(seconds: 20)),
      }),
    );

    expect(find.textContaining('saved map data'), findsNothing);
  });

  testWidgets('shows nothing at all when there is no snapshot', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(wrap(const <String, DateTime>{}));
    expect(find.byType(Row), findsNothing);
  });

  testWidgets('reports the OLDEST feed, not the newest', (
    WidgetTester tester,
  ) async {
    // The dangerous version of this widget reassures you with the freshest
    // number while the layer that matters is hours stale.
    await tester.pumpWidget(
      wrap(<String, DateTime>{
        MapSnapshotStore.feedBuoys: ago(const Duration(minutes: 1)),
        MapSnapshotStore.feedWaveAlerts: ago(const Duration(hours: 4)),
      }),
    );

    expect(find.textContaining('4h ago'), findsOneWidget);
  });

  testWidgets('says outright when hazard layers are absent', (
    WidgetTester tester,
  ) async {
    // Hazards expire after six hours, so an old snapshot has buoys but no
    // warnings. An empty hazard layer looks identical to "no hazards", and
    // those mean opposite things.
    await tester.pumpWidget(
      wrap(<String, DateTime>{
        MapSnapshotStore.feedBuoys: ago(const Duration(hours: 9)),
      }),
    );

    expect(find.textContaining('NOT included'), findsOneWidget);
    expect(find.textContaining('9h ago'), findsOneWidget);
  });

  testWidgets('escalates past three hours', (WidgetTester tester) async {
    await tester.pumpWidget(
      wrap(<String, DateTime>{
        MapSnapshotStore.feedBuoys: ago(const Duration(minutes: 20)),
        MapSnapshotStore.feedWaveAlerts: ago(const Duration(minutes: 20)),
      }),
    );
    expect(find.byIcon(Icons.history_rounded), findsOneWidget);

    await tester.pumpWidget(
      wrap(<String, DateTime>{
        MapSnapshotStore.feedBuoys: ago(const Duration(hours: 5)),
        MapSnapshotStore.feedWaveAlerts: ago(const Duration(hours: 5)),
      }),
    );
    expect(find.byIcon(Icons.cloud_off_rounded), findsOneWidget);
  });
}

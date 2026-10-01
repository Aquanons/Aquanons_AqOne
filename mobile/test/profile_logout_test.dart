import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:aqone/ui/app_shell.dart';
import 'package:aqone/ui/home_page.dart';
import 'package:aqone/ui/profile_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child) {
  return MaterialApp(
    locale: const Locale('en'),
    supportedLocales: kSupportedLocales,
    localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
      ...kFallbackDelegates,
    ],
    home: child,
  );
}

class _FakeSosService extends SosService {
  _FakeSosService()
      : super(
          outbox: OutboxStore(AppDatabase()),
          identity: IdentityStore(AppDatabase()),
          buoy: BuoyClient(),
          backend: BackendClient(),
          location: LocationService(),
        );

  @override
  void start() {}

  @override
  Future<List<SosRecord>> history() async => const <SosRecord>[];
}

void main() {
  testWidgets('logout from the pushed Profile pops it and calls onLogout',
      (tester) async {
    final SemanticsHandle handle = tester.ensureSemantics();
    final t = await AppLocalizations.delegate.load(const Locale('en'));
    var loggedOut = false;
    await tester.pumpWidget(_host(AppShell(
      identity: const VesselIdentity(
        vesselId: 'v-test',
        boat: 'Test Boat',
        skipperName: 'Skipper',
      ),
      sos: _FakeSosService(),
      feeds: VentureFeeds(backend: BackendClient()),
      location: LocationService(),
      identityStore: IdentityStore(AppDatabase()),
      themeMode: ThemeMode.light,
      onThemeModeChanged: (_) {},
      onLogout: () => loggedOut = true,
      onIdentityUpdated: (_) {},
    )));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    await tester.tap(find.byIcon(Icons.person_rounded));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(ProfilePage), findsOneWidget);

    for (var i = 0;
        i < 10 && find.text(t.logoutAction).evaluate().isEmpty;
        i++) {
      await tester.drag(
          find.byType(Scrollable).first, const Offset(0, -400));
      await tester.pump();
    }
    await tester.ensureVisible(find.text(t.logoutAction).first);
    await tester.pump();
    await tester.tap(find.text(t.logoutAction).first);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    await tester.tap(find.widgetWithText(TextButton, t.logoutAction));
    await tester.pump();
    for (var i = 0;
        i < 10 && find.byType(ProfilePage).evaluate().isNotEmpty;
        i++) {
      await tester.pump(const Duration(milliseconds: 300));
    }

    expect(loggedOut, isTrue);
    expect(find.byType(ProfilePage), findsNothing);
    expect(find.byType(HomePage), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    handle.dispose();
  });
}

import 'dart:convert';

import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/ui/profile_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Widget _hostPage(Widget page) {
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
    home: page,
  );
}

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfiNoIsolate;
  });

  testWidgets('409 server rejection makes SnackBar text and Pair action appear after Save', (tester) async {
    final client = MockClient((_) async => http.Response('{"detail":"conflict"}', 409));
    final db = AppDatabase(overridePath: inMemoryDatabasePath);
    final store = IdentityStore(db);
    const identity = VesselIdentity(
      vesselId: '0123456789abcdef0123456789abcdef',
      boat: 'NW-001',
      skipperName: 'Old Skipper',
      phone: '09171234567',
    );

    await tester.pumpWidget(
      _hostPage(
        ProfilePage(
          identityStore: store,
          identity: identity,
          backendClient: BackendClient(client: client),
          themeMode: ThemeMode.light,
          onThemeModeChanged: (_) {},
          onIdentityUpdated: (_) {},
          onLogout: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.edit_rounded));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Save changes'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save changes'));
    await tester.pumpAndSettle();

    expect(
      find.text('Saved on this phone only. The rescue centre still has your old details. Pair this phone to update them.'),
      findsOneWidget,
    );
    expect(find.text('Pair'), findsOneWidget);
    expect(find.text('Profile updated'), findsNothing);
  });

  testWidgets('200 acceptance does not show the Pair action', (tester) async {
    final client = MockClient((_) async => http.Response(jsonEncode({'vessel_id': '0123456789abcdef0123456789abcdef'}), 200));
    final db = AppDatabase(overridePath: inMemoryDatabasePath);
    final store = IdentityStore(db);
    const identity = VesselIdentity(
      vesselId: '0123456789abcdef0123456789abcdef',
      boat: 'NW-001',
      skipperName: 'Old Skipper',
      phone: '09171234567',
    );

    await tester.pumpWidget(
      _hostPage(
        ProfilePage(
          identityStore: store,
          identity: identity,
          backendClient: BackendClient(client: client),
          themeMode: ThemeMode.light,
          onThemeModeChanged: (_) {},
          onIdentityUpdated: (_) {},
          onLogout: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.edit_rounded));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Save changes'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save changes'));
    await tester.pumpAndSettle();

    expect(
      find.text('Saved on this phone only. The rescue centre still has your old details. Pair this phone to update them.'),
      findsNothing,
    );
    expect(find.text('Pair'), findsNothing);
    expect(find.text('Profile updated'), findsOneWidget);
  });
}

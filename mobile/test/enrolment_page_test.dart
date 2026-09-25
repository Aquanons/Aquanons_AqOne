import 'dart:convert';
import 'dart:io';

import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/ui/enrolment_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

class _FakeClient extends http.BaseClient {
  _FakeClient(this._handler);

  final Future<http.StreamedResponse> Function(http.BaseRequest request) _handler;
  int calls = 0;
  http.BaseRequest? lastRequest;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    calls += 1;
    lastRequest = request;
    return _handler(request);
  }
}

Future<http.StreamedResponse> _jsonResponse(
  int statusCode,
  Object body,
) async {
  final bytes = utf8.encode(jsonEncode(body));
  return http.StreamedResponse(
    Stream<List<int>>.value(bytes),
    statusCode,
    headers: const {'content-type': 'application/json'},
  );
}

Widget _wrap(Widget child) {
  return MaterialApp(
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
      ...kFallbackDelegates,
    ],
    supportedLocales: const [Locale('en')],
    home: child,
  );
}

void main() {
  testWidgets('a valid code calls enrollVesselDevice and shows enrolVerified', (tester) async {
    final client = _FakeClient(
      (_) => _jsonResponse(
        200,
        <String, Object?>{
          'token': 'paired-token',
          'expires_at': '2026-08-17T05:00:00Z',
          'device': <String, Object?>{
            'id': 12,
            'vessel_id': 'vessel-123',
            'label': 'Handset',
          },
        },
      ),
    );
    final backend = BackendClient(client: client);

    await tester.pumpWidget(
      _wrap(
        EnrolmentPage(
          backendClient: backend,
          vesselId: 'vessel-123',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final BuildContext context = tester.element(find.byType(EnrolmentPage));
    final t = AppLocalizations.of(context);

    await tester.enterText(find.byType(TextField), 'K7Q4M9PX');
    await tester.tap(find.byType(ElevatedButton));
    await tester.pumpAndSettle();

    expect(client.calls, 1);
    expect(find.text(t.enrolVerified), findsOneWidget);
  });

  testWidgets('a 401 shows enrolCodeInvalid', (tester) async {
    final client = _FakeClient(
      (_) => _jsonResponse(
        401,
        <String, Object?>{'detail': 'invalid code'},
      ),
    );
    final backend = BackendClient(client: client);

    await tester.pumpWidget(
      _wrap(
        EnrolmentPage(
          backendClient: backend,
          vesselId: 'vessel-123',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final BuildContext context = tester.element(find.byType(EnrolmentPage));
    final t = AppLocalizations.of(context);

    await tester.enterText(find.byType(TextField), 'WRONGCODE');
    await tester.tap(find.byType(ElevatedButton));
    await tester.pumpAndSettle();

    expect(find.text(t.enrolCodeInvalid), findsOneWidget);
  });

  testWidgets('no internet shows enrolNeedsInternet', (tester) async {
    final client = _FakeClient(
      (_) => throw const SocketException('No route to host'),
    );
    final backend = BackendClient(client: client);

    await tester.pumpWidget(
      _wrap(
        EnrolmentPage(
          backendClient: backend,
          vesselId: 'vessel-123',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final BuildContext context = tester.element(find.byType(EnrolmentPage));
    final t = AppLocalizations.of(context);

    await tester.enterText(find.byType(TextField), 'ANYCODE');
    await tester.tap(find.byType(ElevatedButton));
    await tester.pumpAndSettle();

    expect(find.text(t.enrolNeedsInternet), findsOneWidget);
  });
}

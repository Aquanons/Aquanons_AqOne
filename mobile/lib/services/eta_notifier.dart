import 'dart:async';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Puts the MDRRMO's acknowledgement into the system notification shade.
///
/// The in-app `ResponderEtaDialog` only ever reaches a fisher who is looking
/// at the phone; this is the same moment reaching one who is not. Fired once
/// per acknowledgement from the shell's watcher (app_shell.dart), which
/// already deduplicates on `local_id` alongside the dialog.
///
/// Deliberately swallow-and-continue: the notification is optional surface, so
/// a missing plugin channel, a denied permission, or an API refusal must never
/// take down the distress dialog that is the point of the feature. That is
/// also why nothing here is surfaced to the caller.
class EtaNotifier {
  EtaNotifier._();

  static final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  static bool _attempted = false;
  static bool _ready = false;

  static final StreamController<int> _nearbyTaps =
      StreamController<int>.broadcast();
  static Stream<int> get nearbyTaps => _nearbyTaps.stream;

  static String nearbyPayload(int id) => 'nearby:$id';

  static int? broadcastIdFromPayload(String? payload) {
    if (payload == null || !payload.startsWith('nearby:')) {
      return null;
    }
    return int.tryParse(payload.substring('nearby:'.length));
  }

  static void handleNotificationPayload(String? payload) {
    final id = broadcastIdFromPayload(payload);
    if (id != null) {
      _nearbyTaps.add(id);
    }
  }

  static Future<void> ensureInitialized() async {
    if (_attempted) {
      return;
    }
    _attempted = true;
    try {
      const settings = InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      );
      await _plugin.initialize(
        settings,
        onDidReceiveNotificationResponse: (response) {
          handleNotificationPayload(response.payload);
        },
      );
      await _plugin
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
      final launchDetails = await _plugin.getNotificationAppLaunchDetails();
      if (launchDetails?.didNotificationLaunchApp ?? false) {
        handleNotificationPayload(launchDetails?.notificationResponse?.payload);
      }
      _ready = true;
    } catch (_) {
      _ready = false;
    }
  }

  static Future<void> showRescueEta({
    required String title,
    required String body,
  }) async {
    await ensureInitialized();
    if (!_ready) {
      return;
    }
    try {
      const details = NotificationDetails(
        android: AndroidNotificationDetails(
          'rescue_eta',
          'Rescue alerts',
          channelDescription: 'MDRRMO responses to your SOS',
          importance: Importance.high,
          priority: Priority.high,
        ),
      );
      await _plugin.show(1, title, body, details);
    } catch (_) {}
  }

  static Future<void> showNearbyHelp({
    required String title,
    required String body,
    required int broadcastId,
  }) async {
    await ensureInitialized();
    if (!_ready) {
      return;
    }
    try {
      const details = NotificationDetails(
        android: AndroidNotificationDetails(
          'nearby_help',
          'Nearby help alerts',
          channelDescription: 'SOS calls near you that need help',
          importance: Importance.high,
          priority: Priority.high,
        ),
      );
      await _plugin.show(
        100000 + (broadcastId % 100000),
        title,
        body,
        details,
        payload: nearbyPayload(broadcastId),
      );
    } catch (_) {}
  }
}
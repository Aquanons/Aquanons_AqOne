import 'dart:async';

import 'package:flutter_foreground_task/flutter_foreground_task.dart';

import '../data/app_database.dart';
import '../data/identity_store.dart';
import '../data/outbox_store.dart';
import '../models/foreground_policy.dart';
import 'backend_client.dart';
import 'buoy_client.dart';
import 'location_service.dart';
import 'sos_service.dart';

@pragma('vm:entry-point')
void startForegroundTaskCallback() {
  FlutterForegroundTask.setTaskHandler(SosTaskHandler());
}

class SosTaskHandler extends TaskHandler {
  DateTime? _lastUiPing;
  AppDatabase? _db;
  OutboxStore? _outbox;
  SosService? _sosService;

  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {}

  @override
  void onRepeatEvent(DateTime timestamp) async {
    try {
      final isForeground = await FlutterForegroundTask.isAppOnForeground;
      final hasRecentUiPing = _lastUiPing != null &&
          timestamp.difference(_lastUiPing!) < const Duration(seconds: 25);

      if (isForeground || hasRecentUiPing) {
        // Main UI isolate is active and handling retries; do not write concurrently to sqflite.
        return;
      }

      // UI isolate is detached. Ensure retries continue.
      _db ??= AppDatabase();
      _outbox ??= OutboxStore(_db!);
      _sosService ??= SosService(
        outbox: _outbox!,
        identity: IdentityStore(_db!),
        buoy: BuoyClient(),
        backend: BackendClient(),
        location: LocationService(),
      );
      await _sosService!.retryPending();
    } catch (_) {
      // Best-effort in background isolate
    }
  }

  @override
  Future<void> onDestroy(DateTime timestamp, bool isTimeout) async {
    _sosService?.dispose();
    _db = null;
  }

  @override
  void onReceiveData(Object data) {
    _lastUiPing = DateTime.now();
  }
}

class SosForeground {
  SosForeground({
    required OutboxStore outbox,
    required SosService sosService,
    required String Function() titleResolver,
    required String Function() bodyResolver,
  })  : _outbox = outbox,
        _sosService = sosService,
        _titleResolver = titleResolver,
        _bodyResolver = bodyResolver;

  final OutboxStore _outbox;
  final SosService _sosService;
  final String Function() _titleResolver;
  final String Function() _bodyResolver;

  StreamSubscription<void>? _subscription;
  Timer? _pingTimer;
  bool _isRunning = false;

  static void init() {
    try {
      FlutterForegroundTask.initCommunicationPort();
      FlutterForegroundTask.init(
        androidNotificationOptions: AndroidNotificationOptions(
          channelId: 'aqone_sos_foreground',
          channelName: 'AqOne SOS Delivery',
          channelDescription: 'Keeps SOS delivery active while the screen is off',
          channelImportance: NotificationChannelImportance.HIGH,
          priority: NotificationPriority.HIGH,
          onlyAlertOnce: true,
        ),
        iosNotificationOptions: const IOSNotificationOptions(
          showNotification: false,
          playSound: false,
        ),
        foregroundTaskOptions: ForegroundTaskOptions(
          eventAction: ForegroundTaskEventAction.repeat(15000),
          autoRunOnBoot: false,
          autoRunOnMyPackageReplaced: false,
          allowWakeLock: true,
          allowWifiLock: true,
        ),
      );
    } catch (_) {
      // Unsupported in test or non-mobile platforms
    }
  }

  void startListening() {
    _subscription = _sosService.changes.listen((_) => evaluate());
    evaluate();
  }

  Future<void> evaluate() async {
    try {
      final records = await _outbox.all();
      final shouldRun = shouldRunForeground(records);
      if (shouldRun && !_isRunning) {
        await _start();
      } else if (!shouldRun && _isRunning) {
        await _stop();
      }
    } catch (_) {
      // Best effort
    }
  }

  Future<void> _start() async {
    try {
      final title = _titleResolver();
      final body = _bodyResolver();
      if (!await FlutterForegroundTask.isRunningService) {
        await FlutterForegroundTask.startService(
          serviceId: 1001,
          notificationTitle: title,
          notificationText: body,
          callback: startForegroundTaskCallback,
        );
      }
      _isRunning = true;
      _startPingTimer();
    } catch (_) {
      // Ignored in test environment
    }
  }

  Future<void> _stop() async {
    try {
      _stopPingTimer();
      if (await FlutterForegroundTask.isRunningService) {
        await FlutterForegroundTask.stopService();
      }
      _isRunning = false;
    } catch (_) {
      // Ignored
    }
  }

  void _startPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      try {
        FlutterForegroundTask.sendDataToTask({'type': 'ping'});
      } catch (_) {}
    });
  }

  void _stopPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = null;
  }

  Future<void> updateNotification({required String title, required String body}) async {
    try {
      if (await FlutterForegroundTask.isRunningService) {
        await FlutterForegroundTask.updateService(
          notificationTitle: title,
          notificationText: body,
        );
      }
    } catch (_) {}
  }

  void dispose() {
    _subscription?.cancel();
    _stopPingTimer();
  }

  static Future<bool> isIgnoringBatteryOptimizations() async {
    try {
      return await FlutterForegroundTask.isIgnoringBatteryOptimizations;
    } catch (_) {
      return true;
    }
  }

  static Future<bool> requestBatteryExemption() async {
    try {
      if (!await FlutterForegroundTask.isIgnoringBatteryOptimizations) {
        return await FlutterForegroundTask.requestIgnoreBatteryOptimization();
      }
      return true;
    } catch (_) {
      return false;
    }
  }
}

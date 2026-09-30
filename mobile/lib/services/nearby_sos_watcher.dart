import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/config.dart';
import '../data/seen_broadcast_store.dart';
import '../models/nearby_sos.dart';
import 'location_service.dart';
import 'nearby_alarm.dart';

class NearbySosWatcher {
  NearbySosWatcher({
    required Future<List<NearbySos>> Function(double lat, double lon) fetch,
    required Future<Fix?> Function() position,
    required SeenBroadcastStore seen,
    required NearbyAlarm alarm,
    required Future<void> Function(NearbySos item) notify,
  })  : _fetch = fetch,
        _position = position,
        _seen = seen,
        _alarm = alarm,
        _notify = notify;

  final Future<List<NearbySos>> Function(double lat, double lon) _fetch;
  final Future<Fix?> Function() _position;
  final SeenBroadcastStore _seen;
  final NearbyAlarm _alarm;
  final Future<void> Function(NearbySos item) _notify;

  final ValueNotifier<List<NearbySos>> _items =
      ValueNotifier<List<NearbySos>>(const <NearbySos>[]);
  final StreamController<NearbySos> _firstSightings =
      StreamController<NearbySos>.broadcast();
  Timer? _timer;
  bool _hasFix = false;
  bool _polling = false;

  ValueListenable<List<NearbySos>> get items => _items;
  bool get hasFix => _hasFix;
  Stream<NearbySos> get firstSightings => _firstSightings.stream;

  Future<void> poll() async {
    if (_polling) return;
    _polling = true;
    try {
      final List<NearbySos> fetched;
      try {
        final fix = await _position();
        _hasFix = fix != null;
        final lat = fix?.lat ?? AqOneConfig.defaultMapLat;
        final lon = fix?.lon ?? AqOneConfig.defaultMapLon;
        fetched = await _fetch(lat, lon);
      } catch (error) {
        // A lost signal says nothing about emergencies: keep the last list
        // and any ringing alarm until the feed answers again.
        debugPrint('nearby SOS poll failed: $error');
        return;
      }
      _items.value = fetched;

      if (fetched.isEmpty) {
        await _alarm.stop();
        return;
      }

      var hasNew = false;
      for (final item in fetched) {
        final isNew = await _seen.markSeen(item.broadcastId);
        if (isNew) {
          hasNew = true;
          await _notify(item);
          _firstSightings.add(item);
        }
      }

      if (hasNew) {
        await _alarm.start();
      }
    } finally {
      _polling = false;
    }
  }

  void start() {
    unawaited(poll());
    _timer?.cancel();
    _timer = Timer.periodic(AqOneConfig.hazardPollInterval, (_) => poll());
  }

  Future<void> silence() async {
    await _alarm.stop();
  }

  void dispose() {
    _timer?.cancel();
    _firstSightings.close();
    _items.dispose();
  }
}

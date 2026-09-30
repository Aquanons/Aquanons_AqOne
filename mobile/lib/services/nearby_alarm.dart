import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:vibration/vibration.dart';

class NearbyAlarm {
  NearbyAlarm({AudioPlayer? player}) : _player = player ?? AudioPlayer();

  final AudioPlayer _player;
  bool _ringing = false;
  bool _sourceSet = false;

  static const String asset = 'audio/broadcastalarm.mp3';

  static final AudioContext alarmContext = AudioContext(
    android: const AudioContextAndroid(
      usageType: AndroidUsageType.alarm,
      contentType: AndroidContentType.sonification,
    ),
  );

  bool get isRinging => _ringing;

  Future<void> start() async {
    if (_ringing) return;
    _ringing = true;
    unawaited(_startVibration());
    unawaited(_startSound());
  }

  Future<void> _startVibration() async {
    try {
      final hasVibrator = await Vibration.hasVibrator();
      if (hasVibrator != true || !_ringing) return;
      await Vibration.vibrate(
        pattern: const <int>[0, 400, 200, 400, 600],
        repeat: 0,
      );
    } catch (_) {}
  }

  Future<void> _startSound() async {
    try {
      await _player.setAudioContext(alarmContext);
      if (!_sourceSet) {
        await _player.setSource(AssetSource(asset));
        await _player.setReleaseMode(ReleaseMode.loop);
        _sourceSet = true;
      }
      await _player.seek(Duration.zero);
      await _player.resume();
    } catch (_) {
      _sourceSet = false;
    }
  }

  Future<void> stop() async {
    _ringing = false;
    try {
      await Vibration.cancel();
    } catch (_) {}
    try {
      await _player.pause();
    } catch (_) {}
  }

  Future<void> dispose() async {
    await stop();
    await _player.dispose();
  }
}

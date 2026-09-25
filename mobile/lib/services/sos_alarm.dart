import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:vibration/vibration.dart';

/// Vibration + alarm tone for the SOS flow.
///
/// Unlike [SquallAlarm], this one plays a real looping audio file (via
/// `audioplayers`) and a real device vibration pattern (via `vibration`),
/// rather than the built-in `HapticFeedback`/`SystemSound` calls — a
/// distress call is the one place in the app where "as loud and insistent
/// as the phone can manage" is the correct behaviour, not "polite".
///
/// Same caveat as [SquallAlarm]: this only runs while the app is in the
/// foreground. It is not a wake-the-locked-phone push notification.
class SosAlarm {
  SosAlarm({AudioPlayer? player}) : _player = player ?? AudioPlayer();

  final AudioPlayer _player;
  bool _ringing = false;
  bool _sourceSet = false;

  static final AudioContext alarmContext = AudioContext(
    android: const AudioContextAndroid(
      usageType: AndroidUsageType.alarm,
      contentType: AndroidContentType.sonification,
    ),
  );

  AudioContext get audioContext => alarmContext;

  bool get isRinging => _ringing;

  /// Starts the loop. Safe to call repeatedly - a second call while already
  /// ringing is a no-op rather than restarting the sound from zero.
  Future<void> start() async {
    if (_ringing) {
      return;
    }
    _ringing = true;

    // Vibration and sound are independent best-effort calls: a phone with no
    // vibration motor (or a plugin that fails on an unusual device) must
    // still get the sound, and vice versa.
    unawaited(_startVibration());
    unawaited(_startSound());
  }

  Future<void> _startVibration() async {
    try {
      final hasVibrator = await Vibration.hasVibrator();
      if (hasVibrator != true || !_ringing) {
        return;
      }
      // Two sharp pulses then a pause, repeating from index 0 - insistent
      // without being a single continuous buzz that fades into the
      // background of a pocket.
      await Vibration.vibrate(
        pattern: const <int>[0, 400, 200, 400, 600],
        repeat: 0,
      );
    } catch (_) {
      // No vibration motor, or the platform does not support it. The sound
      // alone still carries the alarm.
    }
  }

  Future<void> _startSound() async {
    try {
      await _player.setAudioContext(alarmContext);
      if (!_sourceSet) {
        await _player.setSource(AssetSource('audio/sos_alarm.wav'));
        await _player.setReleaseMode(ReleaseMode.loop);
        _sourceSet = true;
      }
      await _player.seek(Duration.zero);
      await _player.resume();
    } catch (_) {
      _sourceSet = false;
    }
  }

  /// Stops both vibration and sound. Called the moment the fisher resolves
  /// the follow-up screen - by cancelling, standing down, or confirming -
  /// so the alarm never keeps ringing after the fisher has already dealt
  /// with it.
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

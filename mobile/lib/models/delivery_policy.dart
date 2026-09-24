import 'delivery_state.dart';
import 'sos_record.dart';

enum SosRoute { pod, direct }

const directBackoff = <Duration>[
  Duration(seconds: 20),
  Duration(seconds: 60),
  Duration(minutes: 5),
];

const podDeliveryDeadline = Duration(minutes: 10);
const staleAfter = Duration(hours: 12);

Set<SosRoute> routesDue(SosRecord record, DateTime now) {
  if (record.state == DeliveryState.saved) {
    return const <SosRoute>{SosRoute.pod, SosRoute.direct};
  }

  if (record.state == DeliveryState.delivered ||
      record.state == DeliveryState.acknowledged) {
    return const <SosRoute>{};
  }

  if (record.state == DeliveryState.relayed) {
    final relayedAt = record.relayedAt;
    final podTimedOut = relayedAt != null &&
        now.toUtc().difference(
              DateTime.fromMillisecondsSinceEpoch(
                relayedAt * 1000,
                isUtc: true,
              ),
            ) >=
            podDeliveryDeadline;

    if (podTimedOut) {
      return const <SosRoute>{SosRoute.direct, SosRoute.pod};
    }

    final lastAttempt = _lastAttemptTime(record);
    final elapsed = now.toUtc().difference(lastAttempt);
    final step = (record.attempts > 1 ? record.attempts - 1 : 0)
        .clamp(0, directBackoff.length - 1);
    final backoff = directBackoff[step];

    if (elapsed >= backoff) {
      return const <SosRoute>{SosRoute.direct};
    }
  }

  return const <SosRoute>{};
}

DateTime _lastAttemptTime(SosRecord record) {
  if (record.lastAttemptAt != null) {
    return DateTime.fromMillisecondsSinceEpoch(
      record.lastAttemptAt! * 1000,
      isUtc: true,
    );
  }
  if (record.relayedAt != null) {
    return DateTime.fromMillisecondsSinceEpoch(
      record.relayedAt! * 1000,
      isUtc: true,
    );
  }
  return record.createdAt.toUtc();
}

bool isStale(SosRecord record, DateTime now) {
  if (record.state != DeliveryState.saved) {
    return false;
  }
  final age = now.toUtc().difference(record.createdAt.toUtc());
  return age > staleAfter;
}

import 'package:aqone/l10n/app_localizations.dart';

/// Why the last delivery attempt of a saved SOS failed.
///
/// Stored in the outbox's `last_error` column as [wire] codes, never as
/// sentences, so the status card can explain it in whatever language the
/// fisher reads - including one picked after the attempt was recorded.
enum DeliveryFailure {
  noSignal('no_signal'),
  noInternet('no_internet'),
  insecure('tls'),
  serverError('server_error'),
  unreachable('unreachable'),
  buoyNotConnected('buoy_not_connected'),
  noBuoy('no_buoy'),
  buoyRejected('buoy_rejected'),
  buoyInvalid('buoy_invalid');

  const DeliveryFailure(this.wire);

  final String wire;

  static String encode(List<DeliveryFailure> failures) =>
      failures.map((DeliveryFailure f) => f.wire).join(',');
}

extension DeliveryFailureL10n on DeliveryFailure {
  String label(AppLocalizations t) => switch (this) {
        DeliveryFailure.noSignal => t.deliveryFailureNoSignal,
        DeliveryFailure.noInternet => t.deliveryFailureNoInternet,
        DeliveryFailure.insecure => t.deliveryFailureInsecure,
        DeliveryFailure.serverError => t.deliveryFailureServerError,
        DeliveryFailure.unreachable => t.deliveryFailureUnreachable,
        DeliveryFailure.buoyNotConnected => t.deliveryFailureBuoyNotConnected,
        DeliveryFailure.noBuoy => t.deliveryFailureNoBuoy,
        DeliveryFailure.buoyRejected => t.deliveryFailureBuoyRejected,
        DeliveryFailure.buoyInvalid => t.deliveryFailureBuoyInvalid,
      };
}

/// The "Last attempt" line for a stored `last_error` value. Rows written
/// before the codes existed hold English text and are shown as written.
String deliveryFailureText(AppLocalizations t, String stored) {
  final List<String> labels = <String>[];
  for (final String code in stored.split(',')) {
    final DeliveryFailure? failure = DeliveryFailure.values
        .where((DeliveryFailure f) => f.wire == code)
        .firstOrNull;
    if (failure == null) {
      return stored;
    }
    labels.add(failure.label(t));
  }
  return labels.join(' · ');
}

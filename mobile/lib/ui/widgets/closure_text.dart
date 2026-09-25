import 'package:aqone/l10n/app_localizations.dart';

/// Maps the backend's resolution code to a localized user-facing closure message.
String closureMessage(AppLocalizations l, String? code) {
  switch (code) {
    case 'rescued':
    case 'safe_confirmed':
    case 'stood_down_by_fisher':
      return l.sosClosedByMdrrmo;
    case 'duplicate':
      return l.sosClosedDuplicate;
    default:
      return l.sosClosedUnconfirmed;
  }
}

import '../../l10n/app_localizations.dart';

/// A bare age such as "4h", for strings that supply their own "ago".
String shortAge(AppLocalizations t, Duration age) {
  if (age.inHours < 1) {
    return t.ageMinutes(age.inMinutes);
  }
  if (age.inDays < 1) {
    return t.ageHours(age.inHours);
  }
  return t.ageDays(age.inDays);
}

/// How long ago something was, such as "4h ago" or "just now".
String ageAgo(AppLocalizations t, Duration age) =>
    age.inMinutes < 1 ? t.ageJustNow : t.ageAgo(shortAge(t, age));

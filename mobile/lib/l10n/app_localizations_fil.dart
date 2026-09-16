// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Filipino Pilipino (`fil`).
class AppLocalizationsFil extends AppLocalizations {
  AppLocalizationsFil([String locale = 'fil']) : super(locale);

  @override
  String get languageSettingTitle => 'Wika';

  @override
  String get languageSettingSubtitle =>
      'Piliin ang wikang gagamitin sa buong app';

  @override
  String get languagePickerPrompt => 'Piliin ang iyong wika';

  @override
  String get navHome => 'Home';

  @override
  String get navVenture => 'Paglalayag';

  @override
  String get navAdvisories => 'Mga Abiso';

  @override
  String get navProfile => 'Profile';

  @override
  String get deliveryStateSavedTitle => 'Naka-save';

  @override
  String get deliveryStateSavedDescription =>
      'Hindi pa naipapadala — walang malapit na buoy. Awtomatikong ipapadala.';

  @override
  String get deliveryStateRelayedTitle => 'Naipasa';

  @override
  String get deliveryStateRelayedDescription =>
      'Naibigay na sa buoy. Naghihintay sa radyo.';

  @override
  String get deliveryStateDeliveredTitle => 'Naihatid';

  @override
  String get deliveryStateDeliveredDescription =>
      'Natanggap na ng dashboard ng MDRRMO.';

  @override
  String get deliveryStateAcknowledgedTitle => 'Sinagot';

  @override
  String get deliveryStateAcknowledgedDescription =>
      'Nakita na ng responder ang SOS na ito.';

  @override
  String get deliveryMetaPosition => 'Posisyon';

  @override
  String get deliveryMetaBuoy => 'Buoy';

  @override
  String get deliveryMetaNote => 'Tala';

  @override
  String get deliveryMetaResponder => 'Responder';

  @override
  String get deliveryMetaEta => 'ETA ng pagsagip';

  @override
  String get deliveryMetaLastAttempt => 'Huling subok';

  @override
  String get deliveryNoGpsFix => 'Walang naitalang GPS';

  @override
  String get seaStatusSafeHeadline => 'Ligtas Lumabas';

  @override
  String get seaStatusSafeSubtitle => 'Maganda ang kalagayan ng dagat.';

  @override
  String get seaStatusCautionHeadline => 'Mag-ingat - Tingnan ang Abiso';

  @override
  String get seaStatusCautionSubtitle => 'Mag-ingat bago lumabas.';

  @override
  String get seaStatusNotAdvisedHeadline => 'Huwag Lumabas';

  @override
  String get seaStatusNotAdvisedSubtitle =>
      'Manatili sa pampang - delikado ang kalagayan.';

  @override
  String get seaStatusUnknownHeadline => 'Wala Pang Abiso';

  @override
  String get seaStatusUnknownSubtitle => 'Tingnan ang mga abiso bago lumabas.';

  @override
  String get crashTitle => 'May naganap na problema';

  @override
  String get crashBody =>
      'Hindi ma-load ang bahaging ito ng screen. Subukang bumalik, o i-restart ang app kung paulit-ulit ito.';

  @override
  String get forecastStripTitle => '7-day outlook';

  @override
  String forecastAsOf(String time) {
    return 'as of $time';
  }

  @override
  String get forecastToday => 'Today';

  @override
  String get forecastDisclaimerNoSeaState =>
      'Forecast guidance from wind and rain only — sea state not available. Not an official PAGASA or MDRRMO call.';

  @override
  String get forecastDisclaimer =>
      'Forecast guidance, not an official PAGASA or MDRRMO call. Always check the sea condition above.';

  @override
  String get riskLevelSafe => 'Safe';

  @override
  String get riskLevelCaution => 'Caution';

  @override
  String get riskLevelDanger => 'Dangerous';

  @override
  String get riskLevelUnknown => 'No data';

  @override
  String get compassNorth => 'N';

  @override
  String get compassEast => 'E';

  @override
  String get compassSouth => 'S';

  @override
  String get compassWest => 'W';

  @override
  String get compassUnavailable => 'Compass unavailable on this device';

  @override
  String get compassNeedsCalibration =>
      'Compass needs calibrating — move the phone in a figure 8';

  @override
  String compassHeading(int degrees) {
    return 'Heading $degrees°';
  }

  @override
  String get hotspotLegendTitle => 'Likely fishing areas';

  @override
  String get hotspotLegendDisclaimer =>
      'Batay sa datos ng kapaligiran. Hindi ito pangako ng huli, at hindi rin ito hudyat ng ligtas na paglabas.';

  @override
  String get onboardingWelcomeBack => 'Maligayang pagbabalik';

  @override
  String get onboardingRegisterBoat => 'Irehistro ang iyong bangka';

  @override
  String get onboardingReturningBody =>
      'Tiyaking tama pa rin ang iyong mga detalye. I-update ang anumang nagbago.';

  @override
  String get onboardingIntroBody =>
      'Walang password. Kasama ang mga detalyeng ito sa iyong SOS upang malaman ng MDRRMO kung sino ang hahanapin.';

  @override
  String get onboardingSaveError =>
      'Hindi ma-save ang iyong mga detalye. Pakisubukan muli.';

  @override
  String get fieldFullName => 'Buong pangalan';

  @override
  String get fieldBoatNameOrRegistration => 'Pangalan o rehistro ng bangka';

  @override
  String get fieldRegistrationType => 'Uri ng rehistro';

  @override
  String fieldRegistrationNumber(String type) {
    return 'Numero ng $type';
  }

  @override
  String get fieldMobileNumber => 'Numero ng mobile';

  @override
  String get actionContinue => 'Magpatuloy';

  @override
  String get helpSupport => 'Tulong at Suporta';

  @override
  String get aboutAqOne => 'Tungkol sa AqOne';

  @override
  String get safetyNotice => 'Paunawa sa kaligtasan';

  @override
  String get agreementPrefix => 'Sa pagpapatuloy, sumasang-ayon ka sa';

  @override
  String get privacyPolicy => 'Patakaran sa Privacy';

  @override
  String get agreementAnd => ' at ';

  @override
  String get termsOfUse => 'Mga Tuntunin ng Paggamit';

  @override
  String get rememberDevice => 'Tandaan ako sa device na ito';

  @override
  String get identityUnverifiedNotice =>
      'Hindi masusuri ng AqOne ang mga detalyeng ito laban sa BFAR o sa iyong LGU. Itinatala ang mga ito bilang sarili mong deklarasyon at ipinapakita sa MDRRMO kasama ng iyong SOS. Ang pagpapadala ng maling distress call ay isang paglabag.';

  @override
  String get licenseBoatRHint =>
      'Rehistro ng munisipal na bangka (3 GT pababa)';

  @override
  String get licenseFishRHint =>
      'Numero ng rehistro ng munisipal na mangingisda';

  @override
  String get licenseCfvglHint =>
      'Lisensya ng komersyal na sasakyang-dagat (3.1 GT pataas)';

  @override
  String get licenseNoneLabel => 'Hindi pa rehistrado';

  @override
  String get licenseNoneHint =>
      'Maaari mo itong idagdag sa settings sa ibang pagkakataon';

  @override
  String get trustSelfDeclared => 'Sariling deklarasyon';

  @override
  String get trustPhoneVerified => 'Beripikado ang telepono';

  @override
  String get trustResponderConfirmed => 'Kinumpirma ng responder';

  @override
  String get validatorFullNameRequired => 'Ilagay ang iyong buong pangalan';

  @override
  String get validatorNameTooShort => 'Masyadong maikli ang pangalang iyon';

  @override
  String validatorMaxCharacters(int max) {
    return 'Panatilihin ito sa ilalim ng $max character';
  }

  @override
  String get validatorNameNotNumber =>
      'Ilagay ang iyong pangalan, hindi numero';

  @override
  String get validatorBoatRequired => 'Ilagay ang pangalan ng iyong bangka';

  @override
  String get validatorMobileRequired => 'Ilagay ang numero ng mobile';

  @override
  String get validatorMobileInvalid =>
      'Maglagay ng PH mobile number, hal. 0912 345 6789';

  @override
  String validatorLicenseRequired(String type, String noneLabel) {
    return 'Ilagay ang numero ng $type, o piliin ang ‘$noneLabel’';
  }

  @override
  String validatorLicenseTooShort(String type) {
    return 'Masyadong maikli ang numero ng $type';
  }

  @override
  String validatorLicenseTooLong(String type) {
    return 'Masyadong mahaba ang numero ng $type';
  }

  @override
  String get validatorLicenseCharacters =>
      'Gumamit lamang ng letra, numero, at gitling';

  @override
  String validatorLicenseDigit(String type) {
    return 'Dapat may kahit isang digit ang numero ng $type';
  }

  @override
  String get validatorFishrDigitsOnly => 'Mga digit lamang ang numero ng FishR';

  @override
  String get profileTitle => 'Profile';

  @override
  String get profileEdit => 'I-edit ang profile';

  @override
  String get profileUpdated => 'Na-update ang profile';

  @override
  String get profileNoName => 'Walang nakalagay na pangalan';

  @override
  String get profileBoatName => 'Pangalan ng bangka';

  @override
  String get profileVesselId => 'ID ng sasakyang-dagat';

  @override
  String get settingsTitle => 'Mga Setting';

  @override
  String get darkMode => 'Dark mode';

  @override
  String get actionCancel => 'Kanselahin';

  @override
  String get actionSaveChanges => 'I-save ang mga pagbabago';

  @override
  String get profileEditTrustNotice =>
      'Kapag in-edit ang iyong mga detalye, babalik sa sariling deklarasyon ang antas ng tiwala. Kailangang kumpirmahing muli ng responder ang iyong pagkakakilanlan.';

  @override
  String get logoutAction => 'Mag-log out';

  @override
  String get logoutConfirmation =>
      'Kailangan mong magrehistro muli upang magamit ang AqOne. Mananatili sa device na ito ang iyong kasaysayan ng SOS.';

  @override
  String get avatarUpdateError =>
      'Hindi ma-update ang iyong larawan sa profile.';

  @override
  String get avatarTakePhoto => 'Kumuha ng larawan';

  @override
  String get avatarChooseGallery => 'Pumili mula sa gallery';

  @override
  String get avatarRemovePhoto => 'Alisin ang larawan';

  @override
  String get responderStatusReceived => 'Natanggap ng MDRRMO ang iyong tawag';

  @override
  String get responderStatusDispatched => 'Papunta na ang bangkang panagip';

  @override
  String get responderStatusCoastGuard => 'Naabisuhan na ang Coast Guard';

  @override
  String get responderStatusNearestVessel =>
      'Naalertuhan na ang mga malapit na bangka';

  @override
  String get responderStatusDelayed => 'Naantala — papunta pa rin';

  @override
  String get responderReplyStillInDanger => 'Nasa panganib pa rin';

  @override
  String get responderReplySafeNow => 'Ligtas na';

  @override
  String get responderReplyConfirmBody =>
      'Sasabihin nito sa MDRRMO na hindi mo na kailangan ng sagip, at maaari nilang ipadala ang tulong sa iba. Kumpirmahin lamang kung talagang ligtas ka na.';

  @override
  String get responderReplyConfirmConfirm => 'Oo, ligtas ako';

  @override
  String get responderReplySentStillInDanger =>
      'Alam ng MDRRMO na naghihintay ka pa rin ng tulong.';

  @override
  String get responderReplySentSafeNow =>
      'Nasabihan na ang MDRRMO na ligtas ka na.';

  @override
  String get responderReplyPending =>
      'Hindi pa naipapadala — awtomatikong ipapadala kapag may koneksyon na.';

  @override
  String get chatStatusQueued => 'Nakapila';

  @override
  String get chatStatusSent => 'Naipadala';

  @override
  String get chatStatusSynced => 'Na-sync';

  @override
  String chatCharacterLimitLabel(int used, int max) {
    return '$used/$max';
  }

  @override
  String get squallStaleTitle =>
      'Pagtataya ng unos: hindi kumpirmado ang katayuan';

  @override
  String squallStaleBodyWithAge(String age) {
    return 'Huling nalamang babasahin: $age na ang nakalipas. Wala munang ipapakitang katayuan ng unos ngayon.';
  }

  @override
  String get squallStaleBodyNoAge =>
      'Wala munang ipapakitang katayuan ng unos ngayon.';

  @override
  String get weatherWindowTitle => 'Fishing weather window';

  @override
  String get weatherWindowLowerRisk => 'Lower forecast risk';

  @override
  String get weatherWindowCautionNow => 'Conditions need caution now';

  @override
  String get weatherWindowCautionSubtitle => 'Prepare and check advisories.';

  @override
  String get weatherWindowDangerNow => 'High-risk conditions now';

  @override
  String get weatherWindowDangerSubtitle => 'Follow MDRRMO guidance.';

  @override
  String weatherWindowWorsenPrefix(String duration) {
    return 'Conditions may worsen in about $duration';
  }

  @override
  String get weatherWindowWithinHour => 'within an hour';

  @override
  String weatherWindowDurationDaysHours(int days, int hours) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days days',
      one: '1 day',
    );
    String _temp1 = intl.Intl.pluralLogic(
      hours,
      locale: localeName,
      other: '$hours hours',
      one: '1 hour',
    );
    return '$_temp0 $_temp1';
  }

  @override
  String weatherWindowDurationDaysOnly(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days days',
      one: '1 day',
    );
    return '$_temp0';
  }

  @override
  String weatherWindowDurationHoursOnly(int hours) {
    String _temp0 = intl.Intl.pluralLogic(
      hours,
      locale: localeName,
      other: '$hours hours',
      one: '1 hour',
    );
    return '$_temp0';
  }

  @override
  String weatherWindowUpcoming(String time, String cause) {
    return 'From $time: $cause';
  }

  @override
  String get weatherWindowReturnTravelDisclaimer =>
      'Does not include return travel or preparation time.';

  @override
  String weatherWindowNoWorsening(String time) {
    return 'No worsening forecast through $time';
  }

  @override
  String get weatherWindowNoWorseningSubtitle =>
      'Near-term forecast remains low risk.';

  @override
  String get weatherWindowEarlierMissing => 'Earlier conditions unavailable';

  @override
  String get weatherWindowEarlierMissingSubtitle =>
      'Earlier hourly conditions unavailable — continuous window cannot be calculated.';

  @override
  String get weatherWindowDailyOnly =>
      'Hourly estimate unavailable from daily forecast';

  @override
  String weatherWindowDailyAdverse(String day) {
    return 'Higher risk forecast on $day; hourly estimate unavailable';
  }

  @override
  String get weatherWindowIncomplete => 'Forecast estimate incomplete';

  @override
  String get weatherWindowIncompleteSubtitle =>
      'Missing hourly wave or wind data. Tap to refresh.';

  @override
  String get weatherWindowRefreshNeeded => 'Forecast refresh needed';

  @override
  String get weatherWindowRefreshNeededSubtitle =>
      'Forecast is over 30 minutes old. Tap to refresh.';

  @override
  String get weatherWindowExpired => 'Forecast expired';

  @override
  String get weatherWindowExpiredSubtitle =>
      'Cached forecast is over 12 hours old. Refresh needed.';

  @override
  String get weatherWindowClockSkew => 'Forecast timestamp unavailable';

  @override
  String get weatherWindowClockSkewSubtitle =>
      'Device clock or forecast timestamp is out of sync.';

  @override
  String get weatherWindowNoForecast => 'Weather window unavailable';

  @override
  String get weatherWindowNoForecastSubtitle =>
      'No forecast data available. Tap to load.';

  @override
  String weatherWindowLocationLabel(String location) {
    return 'Forecast location: $location';
  }

  @override
  String get deteriorationReasonStrongWinds => 'stronger winds';

  @override
  String get deteriorationReasonHighWaves => 'higher waves';

  @override
  String get deteriorationReasonThunderstorm => 'thunderstorms';

  @override
  String get deteriorationReasonHeavyRain => 'heavy rain';

  @override
  String get deteriorationReasonPoorVisibility => 'poor visibility';

  @override
  String get deteriorationReasonDailyRain => 'heavy daily rain';

  @override
  String get deteriorationReasonOfficialCaution => 'official caution';

  @override
  String get deteriorationReasonOfficialDanger =>
      'official warning: not advised';

  @override
  String get deteriorationReasonSquallWatch => 'squall watch';

  @override
  String get deteriorationReasonSquallDanger => 'squall danger: return now';

  @override
  String get weatherLoading => 'Loading weather…';

  @override
  String get weatherUnavailable => 'Weather unavailable';

  @override
  String get weatherRetry => 'Retry';

  @override
  String get weatherLocationYourPosition => 'your position';

  @override
  String get weatherLocationDefault => 'Aklan (default)';

  @override
  String get sosCancelledNothingSent => 'Kinansela ang SOS. Walang naipadala.';

  @override
  String get sosSetupBoatRequired =>
      'Tapusin ang pagrehistro ng iyong bangka bago magpadala ng SOS.';

  @override
  String get responderDelayedStillOnWay => 'Naantala — papunta pa rin';

  @override
  String get rescueNotifTitle => 'Papunta na ang tulong';

  @override
  String rescueNotifBodyMinutes(int minutes) {
    String _temp0 = intl.Intl.pluralLogic(
      minutes,
      locale: localeName,
      other: '$minutes minuto',
      one: '1 minuto',
    );
    return 'Darating ang bangkang panagip sa $_temp0';
  }

  @override
  String get rescueNotifBodySoon =>
      'Darating ang bangkang panagip anumang oras.';

  @override
  String get rescueNotifBodyDelayed =>
      'Naantala ang bangkang panagip ngunit papunta pa rin. Manatili sa iyong bangka.';

  @override
  String get resolvedTitle => 'Nalutas na ang insidente';

  @override
  String get resolvedNotifBody =>
      'Isinara na ng MDRRMO ang insidenteng ito. Kung kailangan mo pa rin ng tulong, magpadala ng bagong SOS.';

  @override
  String get resolvedDescription =>
      'Isinara na ng MDRRMO ang insidenteng ito. Hindi na kailangan ang pagliligtas.';

  @override
  String get cropPhotoTitle => 'Position your photo';

  @override
  String get cropPhotoHint => 'Drag to move · pinch to zoom';

  @override
  String get cropPhotoUse => 'Use photo';

  @override
  String get cropPhotoError => 'That image could not be processed.';

  @override
  String get checklistNewTripTitle => 'Start a new trip?';

  @override
  String get checklistNewTripBody =>
      'This unchecks everything on the list so you can go through your gear again. Your items stay - nothing is deleted.';

  @override
  String get checklistStartNewTrip => 'Start new trip';

  @override
  String get checklistResetSnackBar => 'Checklist reset for the next trip.';

  @override
  String get checklistTripTitle => 'Trip checklist';

  @override
  String get checklistNewTripButton => 'New trip';

  @override
  String checklistPackedLabel(int done, int total) {
    return '$done of $total packed';
  }

  @override
  String get checklistEmpty => 'No checklist items yet.';

  @override
  String get checklistAddItem => 'Add an item';

  @override
  String get squallAckButton => 'I\'m heading back';

  @override
  String get squallModelDisclaimer =>
      'This model is still being calibrated on simulated data. Use your own judgement.';

  @override
  String get squallWarningStays =>
      'The warning stays on your screen until the squall passes.';

  @override
  String buoyDisconnectSnack(String ssid) {
    return 'Disconnected from $ssid';
  }

  @override
  String buoyConnectSnack(String ssid) {
    return 'Connected to $ssid';
  }

  @override
  String get gotItButton => 'Got it';

  @override
  String get myLocationTooltip => 'My location';

  @override
  String get tripChecklistTooltip => 'Trip checklist';

  @override
  String get chatWithBoatsTooltip => 'Chat with nearby boats';

  @override
  String get sosDescribeWrong => 'Describe what is wrong';

  @override
  String get etaArrivalOverdue => 'ARRIVAL OVERDUE';

  @override
  String get etaArrivingIn => 'ARRIVING IN';

  @override
  String get stayWithBoat =>
      'Stay with your boat if it is still afloat. It is easier to spot than a person in the water.';

  @override
  String get understoodButton => 'Understood';

  @override
  String get chatHint => 'Type a message…';

  @override
  String get weatherConditionSunny => 'Sunny & Clear';

  @override
  String get weatherConditionPartlyCloudy => 'Partly Cloudy';

  @override
  String get weatherConditionOvercast => 'Overcast';

  @override
  String get weatherConditionFoggy => 'Foggy';

  @override
  String get weatherConditionDrizzle => 'Light Drizzle';

  @override
  String get weatherConditionRainy => 'Rainy';

  @override
  String get weatherConditionHeavyRain => 'Heavy Rain';

  @override
  String get weatherConditionShowers => 'Showers';

  @override
  String get weatherConditionThunderstorm => 'Thunderstorm';

  @override
  String get weatherConditionSevereStorm => 'Severe Storm';

  @override
  String get weatherConditionCalm => 'Sunny & Calm';

  @override
  String get seaConditionStaleLabel => 'may be outdated';
}

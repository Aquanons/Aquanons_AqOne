// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Aklanon (`akl`).
class AppLocalizationsAkl extends AppLocalizations {
  AppLocalizationsAkl([String locale = 'akl']) : super(locale);

  @override
  String get languageSettingTitle => 'Lengguwahe';

  @override
  String get languageSettingSubtitle =>
      'Pilia ro lengguwahe para sa bug-os nga app';

  @override
  String get languagePickerPrompt => 'Pilia ro imong lengguwahe';

  @override
  String get navHome => 'Home';

  @override
  String get navVenture => 'Paglayag';

  @override
  String get navAdvisories => 'Mga Abiso';

  @override
  String get navProfile => 'Profile';

  @override
  String get deliveryStateSavedTitle => 'Nasave';

  @override
  String get deliveryStateSavedDescription =>
      'Owa pa napadaea — waeay malapit nga buoy. Automatiko nga ipapadaea.';

  @override
  String get deliveryStateRelayedTitle => 'Napasa';

  @override
  String get deliveryStateRelayedDescription =>
      'Nahatag ron sa buoy. Nagahueat sa radyo.';

  @override
  String get deliveryStateDeliveredTitle => 'Nadangat';

  @override
  String get deliveryStateDeliveredDescription =>
      'Nabaton ron it dashboard it MDRRMO.';

  @override
  String get deliveryStateAcknowledgedTitle => 'Nasabat';

  @override
  String get deliveryStateAcknowledgedDescription =>
      'Nakita ron it responder ining SOS.';

  @override
  String get deliveryMetaPosition => 'Posisyon';

  @override
  String get deliveryMetaBuoy => 'Buoy';

  @override
  String get deliveryMetaNote => 'Nota';

  @override
  String get deliveryMetaResponder => 'Responder';

  @override
  String get deliveryMetaEta => 'ETA it panagip';

  @override
  String get deliveryMetaLastAttempt => 'Huling pagtinguha';

  @override
  String get deliveryNoGpsFix => 'Waeay narekord nga GPS';

  @override
  String get seaStatusSafeHeadline => 'Ligtas nga Magguwa';

  @override
  String get seaStatusSafeSubtitle => 'Maayad ro kahimtangan it dagat.';

  @override
  String get seaStatusCautionHeadline => 'Mag-andam - Basaha ro Abiso';

  @override
  String get seaStatusCautionSubtitle => 'Mag-andam anay bag-o magguwa.';

  @override
  String get seaStatusNotAdvisedHeadline => 'Indi Magguwa';

  @override
  String get seaStatusNotAdvisedSubtitle =>
      'Magpabilin sa baybay - delikado ro kahimtangan.';

  @override
  String get seaStatusUnknownHeadline => 'Waeay pa nga Abiso';

  @override
  String get seaStatusUnknownSubtitle => 'Basaha ro mga abiso bag-o magguwa.';

  @override
  String get crashTitle => 'May problema nga natabo';

  @override
  String get crashBody =>
      'Indi mabuksan ining parte it screen. Subuki nga magbalik, o i-restart ro app kon padayon ini.';

  @override
  String get forecastStripTitle => '7-adlaw nga panan-awon';

  @override
  String forecastAsOf(String time) {
    return 'hangtod sa $time';
  }

  @override
  String get forecastToday => 'Subong';

  @override
  String get forecastDisclaimerNoSeaState =>
      'Tantiya base sa hangin ag ulan lamang — waeay kahimtangan it dagat. Indi ini opisyal nga tawag it PAGASA ukon MDRRMO.';

  @override
  String get forecastDisclaimer =>
      'Tantiya lamang, indi opisyal nga tawag it PAGASA ukon MDRRMO. Kanunay nga basaha ro kahimtangan it dagat sa ibabaw.';

  @override
  String get riskLevelSafe => 'Ligtas';

  @override
  String get riskLevelCaution => 'Mag-anam';

  @override
  String get riskLevelDanger => 'Delikado';

  @override
  String get riskLevelUnknown => 'Waeay datos';

  @override
  String get compassNorth => 'N';

  @override
  String get compassEast => 'E';

  @override
  String get compassSouth => 'S';

  @override
  String get compassWest => 'W';

  @override
  String get compassUnavailable => 'Waeay kompas sa device nga ini';

  @override
  String get compassNeedsCalibration =>
      'Kailangan i-calibrate ro kompas — ilihok ro telepono sa porma it 8';

  @override
  String compassHeading(int degrees) {
    return '$degrees° nga agianan';
  }

  @override
  String get hotspotLegendTitle => 'Mga lugar nga may isda';

  @override
  String get hotspotLegendDisclaimer =>
      'Base sa datos it kapalibutan. Indi ini saad it isda, kag indi man ini timailhan nga ligaw eon magguwa.';

  @override
  String get onboardingWelcomeBack => 'Maayad nga pagbalik';

  @override
  String get onboardingRegisterBoat => 'Irehistro ro imong baroto';

  @override
  String get onboardingReturningBody =>
      'Siguruhon nga husto gihapon ro imong mga detalye. Ilisi ro may nagbag-o.';

  @override
  String get onboardingIntroBody =>
      'Waeay password. Kaupod ro mga detalye sa imong SOS agud mahibaluan it MDRRMO kon sin-o ro pangitaon.';

  @override
  String get onboardingSaveError =>
      'Indi ma-save ro imong mga detalye. Palihog magsueod liwat.';

  @override
  String get fieldFullName => 'Bug-os nga ngaran';

  @override
  String get fieldBoatNameOrRegistration => 'Ngaran ukon rehistro it baroto';

  @override
  String get fieldRegistrationType => 'Klase it rehistro';

  @override
  String fieldRegistrationNumber(String type) {
    return 'Numero it $type';
  }

  @override
  String get fieldMobileNumber => 'Numero it mobile';

  @override
  String get actionContinue => 'Magpadayon';

  @override
  String get helpSupport => 'Bulig ag Suporta';

  @override
  String get aboutAqOne => 'Parte sa AqOne';

  @override
  String get safetyNotice => 'Pahibalo sa kaluwasan';

  @override
  String get agreementPrefix => 'Sa pagpadayon, nagauyon ka sa';

  @override
  String get privacyPolicy => 'Patakaran sa Privacy';

  @override
  String get agreementAnd => ' ag ';

  @override
  String get termsOfUse => 'Mga Kondisyon it Paggamit';

  @override
  String get rememberDevice => 'Dumdumon ako sa device nga ini';

  @override
  String get identityUnverifiedNotice =>
      'Indi masusi it AqOne ro mga detalye kontra sa BFAR ukon sa imong LGU. Ginarekord sanda bilang imong kaugalingong deklarasyon ag ginapakita sa MDRRMO kaupod it imong SOS. Ro pagpadala it bueaan nga distress call hay isa ka paglapas.';

  @override
  String get licenseBoatRHint =>
      'Rehistro it municipal nga baroto (3 GT paubos)';

  @override
  String get licenseFishRHint =>
      'Numero it rehistro it municipal nga mananagat';

  @override
  String get licenseCfvglHint =>
      'Lisensya it commercial nga sakayan (3.1 GT paibabaw)';

  @override
  String get licenseNoneLabel => 'Indi pa rehistrado';

  @override
  String get licenseNoneHint => 'Mahimo mo ini idugang sa settings sa ulihi';

  @override
  String get trustSelfDeclared => 'Kaugalingong deklarasyon';

  @override
  String get trustPhoneVerified => 'Nasusi ro telepono';

  @override
  String get trustResponderConfirmed => 'Ginkumpirma it responder';

  @override
  String get validatorFullNameRequired => 'Isueod ro imong bug-os nga ngaran';

  @override
  String get validatorNameTooShort => 'Masadong maikli ro ngaran';

  @override
  String validatorMaxCharacters(int max) {
    return 'Pabilina ini sa idaeom it $max ka karakter';
  }

  @override
  String get validatorNameNotNumber => 'Isueod ro imong ngaran, indi numero';

  @override
  String get validatorBoatRequired => 'Isueod ro ngaran it imong baroto';

  @override
  String get validatorMobileRequired => 'Isueod ro numero it mobile';

  @override
  String get validatorMobileInvalid =>
      'Isueod ro PH mobile number, hal. 0912 345 6789';

  @override
  String validatorLicenseRequired(String type, String noneLabel) {
    return 'Isueod ro numero it $type, ukon pilia ro \'$noneLabel\'';
  }

  @override
  String validatorLicenseTooShort(String type) {
    return 'Masadong maikli ro numero it $type';
  }

  @override
  String validatorLicenseTooLong(String type) {
    return 'Masadong maeaba ro numero it $type';
  }

  @override
  String get validatorLicenseCharacters =>
      'Gamiton eamang ro letra, numero, ag dash';

  @override
  String validatorLicenseDigit(String type) {
    return 'Kinahanglan may bisan sangka digit ro numero it $type';
  }

  @override
  String get validatorFishrDigitsOnly => 'Mga digit eamang ro numero it FishR';

  @override
  String get profileTitle => 'Profile';

  @override
  String get profileEdit => 'Ilisi ro profile';

  @override
  String get profileUpdated => 'Na-update ro profile';

  @override
  String get profileNoName => 'Waeay nakabutang nga ngaran';

  @override
  String get profileBoatName => 'Ngaran it baroto';

  @override
  String get profileVesselId => 'ID it baroto';

  @override
  String get settingsTitle => 'Mga Setting';

  @override
  String get darkMode => 'Madueom nga mode';

  @override
  String get actionCancel => 'Kanselahon';

  @override
  String get actionSaveChanges => 'I-save ro mga pagbag-o';

  @override
  String get profileEditTrustNotice =>
      'Kon ilisan ro imong mga detalye, mabalik sa kaugalingong deklarasyon ro antas it pagsalig. Kinahanglan nga kumpirmahon liwat it responder ro imong pagkakakilanlan.';

  @override
  String get logoutAction => 'Magguwa';

  @override
  String get logoutConfirmation =>
      'Kinahanglan mo magrehistro liwat agud magamit ro AqOne. Magapabilin sa device nga ini ro history it imong SOS.';

  @override
  String get avatarUpdateError => 'Indi ma-update ro imong litrato sa profile.';

  @override
  String get avatarTakePhoto => 'Magkuha it litrato';

  @override
  String get avatarChooseGallery => 'Magpili halin sa gallery';

  @override
  String get avatarRemovePhoto => 'Kuhaa ro litrato';

  @override
  String get responderStatusReceived => 'Nabaton it MDRRMO ro imong tawag';

  @override
  String get responderStatusDispatched =>
      'Nagapakadto ron ro sakayan nga panagip';

  @override
  String get responderStatusCoastGuard => 'Napahibaeuan ron ro Coast Guard';

  @override
  String get responderStatusNearestVessel =>
      'Napahibaeuan ron ro mga hueapit nga sakayan';

  @override
  String get responderStatusDelayed => 'Naulang — nagapakadto pa gihapon';

  @override
  String get responderReplyStillInDanger => 'Peligro pa gihapon';

  @override
  String get responderReplySafeNow => 'Seguro ron';

  @override
  String get responderReplyConfirmBody =>
      'Ini magasugid sa MDRRMO nga waea mo na kinahanglana ro pagsagip, kag mahimo nila ipadaea ro bueig sa iban. Kumpirmahon lamang kon seguro ka gid ron.';

  @override
  String get responderReplyConfirmConfirm => 'Huo, seguro ako';

  @override
  String get responderReplySentStillInDanger =>
      'Naeaman it MDRRMO nga nagahueat ka pa gihapon it bueig.';

  @override
  String get responderReplySentSafeNow =>
      'Napahibaeuan ron ro MDRRMO nga seguro ka ron.';

  @override
  String get responderReplyPending =>
      'Owa pa napadaea — automatiko nga ipapadaea kon may koneksyon ron.';

  @override
  String get chatStatusQueued => 'Nakapila';

  @override
  String get chatStatusSent => 'Napadaea';

  @override
  String get chatStatusSynced => 'Na-sync';

  @override
  String chatCharacterLimitLabel(int used, int max) {
    return '$used/$max';
  }

  @override
  String get squallStaleTitle =>
      'Pagtantiya sa unos: waeay masaligan nga kahimtangan';

  @override
  String squallStaleBodyWithAge(String age) {
    return 'Huling nahibaeuan nga reading: $age na ang nakalabay. Waeay ipakita nga kahimtangan it unos subong.';
  }

  @override
  String get squallStaleBodyNoAge =>
      'Waeay ipakita nga kahimtangan it unos subong.';

  @override
  String get weatherWindowTitle => 'Panahon it pagpangisda';

  @override
  String get weatherWindowLowerRisk => 'Mas ubos nga peligro sa tantiya';

  @override
  String get weatherWindowCautionNow => 'Kinahanglan ro pag-anam subong';

  @override
  String get weatherWindowCautionSubtitle =>
      'Mag-andam ag basaha ro mga abiso.';

  @override
  String get weatherWindowDangerNow => 'Taas nga peligro subong';

  @override
  String get weatherWindowDangerSubtitle => 'Sunda ro instructions it MDRRMO.';

  @override
  String weatherWindowWorsenPrefix(String duration) {
    return 'Mahimong mag-usab ro kahimtangan sa sobra $duration';
  }

  @override
  String get weatherWindowWithinHour => 'sa sulod it sangka oras';

  @override
  String weatherWindowDurationDaysHours(int days, int hours) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days ka adlaw',
      one: '1 ka adlaw',
    );
    String _temp1 = intl.Intl.pluralLogic(
      hours,
      locale: localeName,
      other: '$hours ka oras',
      one: '1 ka oras',
    );
    return '$_temp0 $_temp1';
  }

  @override
  String weatherWindowDurationDaysOnly(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days ka adlaw',
      one: '1 ka adlaw',
    );
    return '$_temp0';
  }

  @override
  String weatherWindowDurationHoursOnly(int hours) {
    String _temp0 = intl.Intl.pluralLogic(
      hours,
      locale: localeName,
      other: '$hours ka oras',
      one: '1 ka oras',
    );
    return '$_temp0';
  }

  @override
  String weatherWindowUpcoming(String time, String cause) {
    return 'Gikan sa $time: $cause';
  }

  @override
  String get weatherWindowReturnTravelDisclaimer =>
      'Indi isama ro pagbalik ukon pag-andam.';

  @override
  String weatherWindowNoWorsening(String time) {
    return 'Waeay pag-usab hangtod sa $time';
  }

  @override
  String get weatherWindowNoWorseningSubtitle =>
      'Ubos pa ro peligro sa tantiya.';

  @override
  String get weatherWindowEarlierMissing => 'Waeay datos sa nauna nga oras';

  @override
  String get weatherWindowEarlierMissingSubtitle =>
      'Waeay datos sa nauna nga oras — indi makuha ro bug-os nga tantiya.';

  @override
  String get weatherWindowDailyOnly =>
      'Waeay tantiya per oras, adlaw-adlaw lamang';

  @override
  String weatherWindowDailyAdverse(String day) {
    return 'Taas nga peligro sa $day; waeay tantiya per oras';
  }

  @override
  String get weatherWindowIncomplete => 'Kulang pa ro tantiya';

  @override
  String get weatherWindowIncompleteSubtitle =>
      'Waeay datos it alon ukon hangin per oras. Pislita agud ma-refresh.';

  @override
  String get weatherWindowRefreshNeeded => 'Kailangan i-refresh ro tantiya';

  @override
  String get weatherWindowRefreshNeededSubtitle =>
      'Labaw sa 30 ka minuto na ro tantiya. Pislita agud ma-refresh.';

  @override
  String get weatherWindowExpired => 'Natapos na ro tantiya';

  @override
  String get weatherWindowExpiredSubtitle =>
      'Labaw sa 12 ka oras na ro tantiya. Kailangan i-refresh.';

  @override
  String get weatherWindowClockSkew => 'Waeay oras it tantiya';

  @override
  String get weatherWindowClockSkewSubtitle =>
      'Indi tugma ro oras it device ukon tantiya.';

  @override
  String get weatherWindowNoForecast => 'Waeay tantiya it panahon';

  @override
  String get weatherWindowNoForecastSubtitle =>
      'Waeay datos it panahon. Pislita agud magsueod.';

  @override
  String weatherWindowLocationLabel(String location) {
    return 'Lokasyon it tantiya: $location';
  }

  @override
  String get deteriorationReasonStrongWinds => 'mas kusog nga hangin';

  @override
  String get deteriorationReasonHighWaves => 'mas taas nga alon';

  @override
  String get deteriorationReasonThunderstorm => 'uran ag kilat';

  @override
  String get deteriorationReasonHeavyRain => 'bug-at nga ulan';

  @override
  String get deteriorationReasonPoorVisibility => 'hinaay nga pagtan-aw';

  @override
  String get deteriorationReasonDailyRain => 'bug-at nga adlaw-adlaw nga ulan';

  @override
  String get deteriorationReasonOfficialCaution => 'opisyal nga pag-anam';

  @override
  String get deteriorationReasonOfficialDanger =>
      'opisyal nga babala: indi magguwa';

  @override
  String get deteriorationReasonSquallWatch => 'bantay it unos';

  @override
  String get deteriorationReasonSquallDanger => 'unos: pauli na';

  @override
  String get weatherLoading => 'Nagsueod it panahon…';

  @override
  String get weatherUnavailable => 'Waeay panahon';

  @override
  String get weatherRetry => 'Sueod liwat';

  @override
  String get weatherLocationYourPosition => 'imong lokasyon';

  @override
  String get weatherLocationDefault => 'Aklan (default)';

  @override
  String get sosCancelledNothingSent => 'Ginkansela ro SOS. Waeay it napadaea.';

  @override
  String get sosSetupBoatRequired =>
      'Tapuson ro pagrehistro it imong baroto bag-o magpadaea it SOS.';

  @override
  String get responderDelayedStillOnWay => 'Naulang — nagapakadto pa gihapon';

  @override
  String get rescueNotifTitle => 'Nagapakadto ron ro bulig';

  @override
  String rescueNotifBodyMinutes(int minutes) {
    String _temp0 = intl.Intl.pluralLogic(
      minutes,
      locale: localeName,
      other: '$minutes ka minuto',
      one: '1 ka minuto',
    );
    return 'Madangat ro sakayan nga panagip sa $_temp0';
  }

  @override
  String get rescueNotifBodySoon =>
      'Madangat sa anumang oras ro sakayan nga panagip.';

  @override
  String get rescueNotifBodyDelayed =>
      'Naulang ro sakayan nga panagip, pero nagapakadto pa gihapon. Pabilin sa imong sakayan.';

  @override
  String get resolvedTitle => 'Nasolbad ron ro insidente';

  @override
  String get resolvedNotifBody =>
      'Gin-pundoe ron it MDRRMO ining insidente. Kon kinahanglan mo pa gihapon it bueig, magpadaea it bag-o nga SOS.';

  @override
  String get resolvedDescription =>
      'Gin-pundoe ron it MDRRMO ining insidente. Indi na kinahanglan ro pagsagip.';

  @override
  String get cropPhotoTitle => 'Ibutang ro imong litrato';

  @override
  String get cropPhotoHint => 'Igiuot agud malihok · gipit agud mag-zoom';

  @override
  String get cropPhotoUse => 'Gamiton ro litrato';

  @override
  String get cropPhotoError => 'Indi maproseso ro litrato.';

  @override
  String get checklistNewTripTitle => 'Magbag-o nga paglayag?';

  @override
  String get checklistNewTripBody =>
      'Tanggungon ro tanan sa lista agud masusi liwat ro imong kagamitan. Magapabilin ro imong mga items — waeay mabutang.';

  @override
  String get checklistStartNewTrip => 'Bag-o nga paglayag';

  @override
  String get checklistResetSnackBar =>
      'Gin-reset ro checklist para sa sunod nga paglayag.';

  @override
  String get checklistTripTitle => 'Checklist it Paglayag';

  @override
  String get checklistNewTripButton => 'Bag-o';

  @override
  String checklistPackedLabel(int done, int total) {
    return '$done sa $total ka nahuhimus';
  }

  @override
  String get checklistEmpty => 'Waeay pa nga items sa checklist.';

  @override
  String get checklistAddItem => 'Dugang item';

  @override
  String get squallAckButton => 'Pauli na ako';

  @override
  String get squallModelDisclaimer =>
      'Ginakalibrate pa ining modelo base sa simulaasyon. Gamiton ro imong kaugalingong hukom.';

  @override
  String get squallWarningStays =>
      'Magapabilin ro babala sa imong screen hangtod mauli ang unos.';

  @override
  String buoyDisconnectSnack(String ssid) {
    return 'Naputol ang koneksyon sa $ssid';
  }

  @override
  String buoyConnectSnack(String ssid) {
    return 'Nakonektar sa $ssid';
  }

  @override
  String get gotItButton => 'Nakasabot';

  @override
  String get myLocationTooltip => 'Akong lokasyon';

  @override
  String get tripChecklistTooltip => 'Checklist it Paglayag';

  @override
  String get chatWithBoatsTooltip => 'I-chat ang mga baroto nga duol';

  @override
  String get sosDescribeWrong => 'Isaysay kung ano ang mali';

  @override
  String get etaArrivalOverdue => 'NAULANG ANG ABOT';

  @override
  String get etaArrivingIn => 'MADANGAT SA';

  @override
  String get stayWithBoat =>
      'Pabilin sa imong sakayan kon buhi pa. Mas hilyo ini makuha kaysa tawo sa tubig.';

  @override
  String get understoodButton => 'Nakasabot';

  @override
  String get chatHint => 'Sulat ug mensahe…';

  @override
  String get weatherConditionSunny => 'Adlaw ag Klaro';

  @override
  String get weatherConditionPartlyCloudy => 'Bahin nga Makapuron';

  @override
  String get weatherConditionOvercast => 'Kapuron';

  @override
  String get weatherConditionFoggy => 'Mabugnaw';

  @override
  String get weatherConditionDrizzle => 'Ga-ulan nga Hinaay';

  @override
  String get weatherConditionRainy => 'Ulanon';

  @override
  String get weatherConditionHeavyRain => 'Bug-at nga Ulan';

  @override
  String get weatherConditionShowers => 'Ulan';

  @override
  String get weatherConditionThunderstorm => 'Uran ag Kilat';

  @override
  String get weatherConditionSevereStorm => 'Grabe nga Unos';

  @override
  String get weatherConditionCalm => 'Adlaw ag Kumuyom';

  @override
  String get seaConditionStaleLabel => 'mahimong outdated na';
}

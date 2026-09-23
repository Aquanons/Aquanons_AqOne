import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_akl.dart';
import 'app_localizations_en.dart';
import 'app_localizations_fil.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('akl'),
    Locale('en'),
    Locale('fil')
  ];

  /// Section heading on the Profile page for the language selector.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get languageSettingTitle;

  /// Helper text under the Language setting on the Profile page.
  ///
  /// In en, this message translates to:
  /// **'Choose the language for the whole app'**
  String get languageSettingSubtitle;

  /// Heading on the first onboarding screen, shown before the user has picked a language. Must be short enough to be guessable by a speaker of any of the three languages.
  ///
  /// In en, this message translates to:
  /// **'Choose your language'**
  String get languagePickerPrompt;

  /// Bottom navigation label for the main SOS screen. Keep short - the bottom bar has four items and overflows easily.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get navHome;

  /// Bottom navigation label for the trip screen with weather, compass and map.
  ///
  /// In en, this message translates to:
  /// **'Venture mode'**
  String get navVenture;

  /// Bottom navigation label for official MDRRMO notices.
  ///
  /// In en, this message translates to:
  /// **'Advisories'**
  String get navAdvisories;

  /// Bottom navigation label for the user's vessel details and settings.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get navProfile;

  /// SAFETY CRITICAL. First of four delivery states. The SOS is on the phone only and has reached nobody. Must not sound reassuring - the user has to understand help is not yet coming.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get deliveryStateSavedTitle;

  /// SAFETY CRITICAL. Explains the Saved state. Two facts: it has not been sent, and the phone will keep trying without the user doing anything.
  ///
  /// In en, this message translates to:
  /// **'Not sent — no buoy nearby. Will send automatically.'**
  String get deliveryStateSavedDescription;

  /// SAFETY CRITICAL. Second of four delivery states. A buoy accepted the SOS and is passing it over the LoRa radio mesh. Nobody has received it yet.
  ///
  /// In en, this message translates to:
  /// **'Relayed'**
  String get deliveryStateRelayedTitle;

  /// SAFETY CRITICAL. Explains the Relayed state. 'Mesh' means the chain of radio buoys - use whatever a fisherman would actually call it, not a literal translation.
  ///
  /// In en, this message translates to:
  /// **'Handed to the buoy. Waiting for the mesh.'**
  String get deliveryStateRelayedDescription;

  /// SAFETY CRITICAL. Third of four delivery states. The MDRRMO dashboard received the SOS, but no human has confirmed seeing it.
  ///
  /// In en, this message translates to:
  /// **'Delivered'**
  String get deliveryStateDeliveredTitle;

  /// SAFETY CRITICAL. Explains the Delivered state. Keep 'MDRRMO' untranslated - it is the official agency acronym.
  ///
  /// In en, this message translates to:
  /// **'Received by the MDRRMO dashboard.'**
  String get deliveryStateDeliveredDescription;

  /// SAFETY CRITICAL. Fourth and final delivery state. A human responder has seen the SOS and is acting on it. This is the only state that means help is coming.
  ///
  /// In en, this message translates to:
  /// **'Acknowledged'**
  String get deliveryStateAcknowledgedTitle;

  /// SAFETY CRITICAL. Explains the Acknowledged state.
  ///
  /// In en, this message translates to:
  /// **'Responder acknowledged this SOS.'**
  String get deliveryStateAcknowledgedDescription;

  /// Row label next to the GPS coordinates of an SOS.
  ///
  /// In en, this message translates to:
  /// **'Position'**
  String get deliveryMetaPosition;

  /// Row label next to the id of the buoy that carried the SOS.
  ///
  /// In en, this message translates to:
  /// **'Buoy'**
  String get deliveryMetaBuoy;

  /// Row label next to the free-text message the user typed with their SOS.
  ///
  /// In en, this message translates to:
  /// **'Note'**
  String get deliveryMetaNote;

  /// Row label next to the name of the MDRRMO responder who acknowledged the SOS.
  ///
  /// In en, this message translates to:
  /// **'Responder'**
  String get deliveryMetaResponder;

  /// SAFETY CRITICAL. Row label next to the countdown the MDRRMO gave for rescue arrival. The number after it is the time until the rescue boat arrives.
  ///
  /// In en, this message translates to:
  /// **'Rescue ETA'**
  String get deliveryMetaEta;

  /// Row label next to the reason the most recent send attempt failed.
  ///
  /// In en, this message translates to:
  /// **'Last attempt'**
  String get deliveryMetaLastAttempt;

  /// Shown in place of coordinates when the phone had no GPS lock at the moment the SOS was sent. The SOS is still valid without it.
  ///
  /// In en, this message translates to:
  /// **'No GPS fix recorded'**
  String get deliveryNoGpsFix;

  /// SAFETY CRITICAL. Official MDRRMO go/no-go call, green. This is a human decision and outranks the app's own weather guess.
  ///
  /// In en, this message translates to:
  /// **'Safe to Go Out'**
  String get seaStatusSafeHeadline;

  /// SAFETY CRITICAL. Default explanation under the Safe headline, used when the MDRRMO gave no reason of their own.
  ///
  /// In en, this message translates to:
  /// **'Sea conditions are favorable.'**
  String get seaStatusSafeSubtitle;

  /// SAFETY CRITICAL. Official MDRRMO call, amber. Not a ban, but the user must read the advisories before deciding.
  ///
  /// In en, this message translates to:
  /// **'Caution - Check Advisories'**
  String get seaStatusCautionHeadline;

  /// SAFETY CRITICAL. Default explanation under the Caution headline.
  ///
  /// In en, this message translates to:
  /// **'Exercise caution before heading out.'**
  String get seaStatusCautionSubtitle;

  /// SAFETY CRITICAL. Official MDRRMO call, red. The strongest warning in the app. Needs a second native-speaker reviewer - understating this in translation is a real hazard.
  ///
  /// In en, this message translates to:
  /// **'Not Advised to Go Out'**
  String get seaStatusNotAdvisedHeadline;

  /// SAFETY CRITICAL. Default explanation under the Not Advised headline. Imperative mood - this is an instruction, not a suggestion.
  ///
  /// In en, this message translates to:
  /// **'Stay ashore - conditions are dangerous.'**
  String get seaStatusNotAdvisedSubtitle;

  /// Shown when the MDRRMO has not published a call, or the phone could not fetch one. Must not read as 'safe'.
  ///
  /// In en, this message translates to:
  /// **'Status Not Yet Set'**
  String get seaStatusUnknownHeadline;

  /// Default explanation under the Status Not Yet Set headline.
  ///
  /// In en, this message translates to:
  /// **'Check advisories before heading out.'**
  String get seaStatusUnknownSubtitle;

  /// Heading on the fallback screen shown when part of the UI fails to build.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get crashTitle;

  /// Body of the crash fallback screen. Deliberately plain - it replaces a Flutter stack trace that a fisherman at sea has no use for.
  ///
  /// In en, this message translates to:
  /// **'This part of the screen couldn\'t load. Try going back, or restart the app if it keeps happening.'**
  String get crashBody;

  /// Heading above the seven day chips on the Home weather card.
  ///
  /// In en, this message translates to:
  /// **'7-day outlook'**
  String get forecastStripTitle;

  /// Shown when the outlook came from the offline cache rather than a live fetch. {time} is a clock time like "6:12 AM". Placeholder must be kept.
  ///
  /// In en, this message translates to:
  /// **'as of {time}'**
  String forecastAsOf(String time);

  /// Label on the first chip of the outlook strip, in place of a weekday name.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get forecastToday;

  /// SAFETY CRITICAL. Footnote under the outlook strip when no wave data was available. Must keep both halves: that sea state is missing, and that this is not an official call.
  ///
  /// In en, this message translates to:
  /// **'Forecast guidance from wind and rain only — sea state not available. Not an official PAGASA or MDRRMO call.'**
  String get forecastDisclaimerNoSeaState;

  /// SAFETY CRITICAL. Footnote under the outlook strip. Must not be softened into sounding like an official advisory.
  ///
  /// In en, this message translates to:
  /// **'Forecast guidance, not an official PAGASA or MDRRMO call. Always check the sea condition above.'**
  String get forecastDisclaimer;

  /// SAFETY CRITICAL. Green day in the outlook strip. Means the forecast shows nothing adverse - NOT that it is safe to go out, which only the MDRRMO sea condition can say.
  ///
  /// In en, this message translates to:
  /// **'Safe'**
  String get riskLevelSafe;

  /// SAFETY CRITICAL. Amber day in the outlook strip.
  ///
  /// In en, this message translates to:
  /// **'Caution'**
  String get riskLevelCaution;

  /// SAFETY CRITICAL. Red day in the outlook strip. Needs a second reviewer - understating this is a real hazard.
  ///
  /// In en, this message translates to:
  /// **'Dangerous'**
  String get riskLevelDanger;

  /// Grey day in the outlook strip: not enough forecast data to judge. Must not read as "fine" or "calm".
  ///
  /// In en, this message translates to:
  /// **'No data'**
  String get riskLevelUnknown;

  /// Single letter for north on the Venture compass dial. Keep to one or two characters - it is drawn inside a 58px dial.
  ///
  /// In en, this message translates to:
  /// **'N'**
  String get compassNorth;

  /// Single letter for east on the Venture compass dial. Keep to one or two characters.
  ///
  /// In en, this message translates to:
  /// **'E'**
  String get compassEast;

  /// Single letter for south on the Venture compass dial. Keep to one or two characters.
  ///
  /// In en, this message translates to:
  /// **'S'**
  String get compassSouth;

  /// Single letter for west on the Venture compass dial. Keep to one or two characters.
  ///
  /// In en, this message translates to:
  /// **'W'**
  String get compassWest;

  /// Tooltip when the handset has no magnetometer, so the dial is greyed out.
  ///
  /// In en, this message translates to:
  /// **'Compass unavailable on this device'**
  String get compassUnavailable;

  /// Tooltip when magnetic field strength is out of range, usually an uncalibrated sensor or a magnet nearby. The figure-8 motion is the standard fix and should stay in the translation.
  ///
  /// In en, this message translates to:
  /// **'Compass needs calibrating — move the phone in a figure 8'**
  String get compassNeedsCalibration;

  /// Tooltip showing the current compass heading. {degrees} is a whole number 0-359. Placeholder must be kept.
  ///
  /// In en, this message translates to:
  /// **'Heading {degrees}°'**
  String compassHeading(int degrees);

  /// Title of the map legend for the modelled hotspot layer. Avoid wording that promises fish.
  ///
  /// In en, this message translates to:
  /// **'Likely fishing areas'**
  String get hotspotLegendTitle;

  /// SAFETY CRITICAL. Sits under the hotspot legend. Both denials must survive translation: no guaranteed catch, and this is not a safety call.
  ///
  /// In en, this message translates to:
  /// **'Based on environmental data. Not a promise of fish, and not a safe-to-go-out signal.'**
  String get hotspotLegendDisclaimer;

  /// Heading on the vessel details screen for a returning user.
  ///
  /// In en, this message translates to:
  /// **'Welcome back'**
  String get onboardingWelcomeBack;

  /// Heading on the first-run vessel registration screen.
  ///
  /// In en, this message translates to:
  /// **'Register your boat'**
  String get onboardingRegisterBoat;

  /// Instructions under the returning-user heading.
  ///
  /// In en, this message translates to:
  /// **'Check your details are still correct. Update them here if anything has changed.'**
  String get onboardingReturningBody;

  /// Explanation under the vessel registration heading. Keep SOS and MDRRMO untranslated.
  ///
  /// In en, this message translates to:
  /// **'No password. These details travel with your SOS so the MDRRMO knows who to look for.'**
  String get onboardingIntroBody;

  /// Error shown when vessel details cannot be saved locally.
  ///
  /// In en, this message translates to:
  /// **'Could not save your details. Please try again.'**
  String get onboardingSaveError;

  /// Label for the skipper's full-name field.
  ///
  /// In en, this message translates to:
  /// **'Full name'**
  String get fieldFullName;

  /// Label for the boat name or registration field.
  ///
  /// In en, this message translates to:
  /// **'Boat name or registration'**
  String get fieldBoatNameOrRegistration;

  /// Label for the registration-type selector.
  ///
  /// In en, this message translates to:
  /// **'Registration type'**
  String get fieldRegistrationType;

  /// Label for a registration number field. {type} is BoatR, FishR, or CFVGL.
  ///
  /// In en, this message translates to:
  /// **'{type} number'**
  String fieldRegistrationNumber(String type);

  /// Label for the skipper's Philippine mobile-number field.
  ///
  /// In en, this message translates to:
  /// **'Mobile number'**
  String get fieldMobileNumber;

  /// Primary button that saves registration and continues into the app.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get actionContinue;

  /// Title and link for the help page.
  ///
  /// In en, this message translates to:
  /// **'Help & Support'**
  String get helpSupport;

  /// Title and link for the AqOne information page.
  ///
  /// In en, this message translates to:
  /// **'About AqOne'**
  String get aboutAqOne;

  /// Link to the safety and terms notice.
  ///
  /// In en, this message translates to:
  /// **'Safety notice'**
  String get safetyNotice;

  /// Text before Privacy Policy and Terms of Use links.
  ///
  /// In en, this message translates to:
  /// **'By continuing you agree to the'**
  String get agreementPrefix;

  /// Link and title for the privacy policy.
  ///
  /// In en, this message translates to:
  /// **'Privacy Policy'**
  String get privacyPolicy;

  /// Connector between Privacy Policy and Terms of Use links. Preserve surrounding spaces.
  ///
  /// In en, this message translates to:
  /// **' and '**
  String get agreementAnd;

  /// Link and title for terms of use.
  ///
  /// In en, this message translates to:
  /// **'Terms of Use'**
  String get termsOfUse;

  /// Checkbox label controlling whether identity remains stored on the phone.
  ///
  /// In en, this message translates to:
  /// **'Remember me on this device'**
  String get rememberDevice;

  /// Warning that registration details are self-declared and false SOS calls are offences. Keep AqOne, BFAR, LGU, MDRRMO, and SOS untranslated.
  ///
  /// In en, this message translates to:
  /// **'AqOne cannot check these details against BFAR or your LGU. They are recorded as your own declaration and shown to the MDRRMO with your SOS. Sending a false distress call is an offence.'**
  String get identityUnverifiedNotice;

  /// Explanation of the BoatR registration option.
  ///
  /// In en, this message translates to:
  /// **'Municipal boat registration (3 GT and below)'**
  String get licenseBoatRHint;

  /// Explanation of the FishR registration option.
  ///
  /// In en, this message translates to:
  /// **'Municipal fisherfolk registration number'**
  String get licenseFishRHint;

  /// Explanation of the CFVGL registration option.
  ///
  /// In en, this message translates to:
  /// **'Commercial vessel licence (3.1 GT and above)'**
  String get licenseCfvglHint;

  /// Registration selector option for a skipper with no available registration.
  ///
  /// In en, this message translates to:
  /// **'Not registered yet'**
  String get licenseNoneLabel;

  /// Explanation under the Not registered yet option.
  ///
  /// In en, this message translates to:
  /// **'You can add this later in settings'**
  String get licenseNoneHint;

  /// Identity trust label when details were entered only on this phone.
  ///
  /// In en, this message translates to:
  /// **'Self-declared'**
  String get trustSelfDeclared;

  /// Identity trust label when the phone number was verified.
  ///
  /// In en, this message translates to:
  /// **'Phone verified'**
  String get trustPhoneVerified;

  /// Identity trust label after a responder confirms the vessel.
  ///
  /// In en, this message translates to:
  /// **'Confirmed by responder'**
  String get trustResponderConfirmed;

  /// Validation error for an empty skipper name.
  ///
  /// In en, this message translates to:
  /// **'Please enter your full name'**
  String get validatorFullNameRequired;

  /// Validation error for a one-character skipper name.
  ///
  /// In en, this message translates to:
  /// **'That name looks too short'**
  String get validatorNameTooShort;

  /// Validation error when a field exceeds its maximum length.
  ///
  /// In en, this message translates to:
  /// **'Please keep this under {max} characters'**
  String validatorMaxCharacters(int max);

  /// Validation error when a skipper name contains no letters.
  ///
  /// In en, this message translates to:
  /// **'Please enter your name, not a number'**
  String get validatorNameNotNumber;

  /// Validation error for an empty boat name.
  ///
  /// In en, this message translates to:
  /// **'Please enter your boat name'**
  String get validatorBoatRequired;

  /// Validation error for an empty mobile number.
  ///
  /// In en, this message translates to:
  /// **'Please enter a mobile number'**
  String get validatorMobileRequired;

  /// Validation error for a malformed Philippine mobile number.
  ///
  /// In en, this message translates to:
  /// **'Enter a PH mobile number, e.g. 0912 345 6789'**
  String get validatorMobileInvalid;

  /// Validation error for an empty required registration number.
  ///
  /// In en, this message translates to:
  /// **'Enter your {type} number, or choose ‘{noneLabel}’'**
  String validatorLicenseRequired(String type, String noneLabel);

  /// Validation error for a short registration number.
  ///
  /// In en, this message translates to:
  /// **'That {type} number looks too short'**
  String validatorLicenseTooShort(String type);

  /// Validation error for a long registration number.
  ///
  /// In en, this message translates to:
  /// **'That {type} number looks too long'**
  String validatorLicenseTooLong(String type);

  /// Validation error for invalid registration-number characters.
  ///
  /// In en, this message translates to:
  /// **'Use letters, numbers and dashes only'**
  String get validatorLicenseCharacters;

  /// Validation error when a registration number has no digit.
  ///
  /// In en, this message translates to:
  /// **'A {type} number contains at least one digit'**
  String validatorLicenseDigit(String type);

  /// Validation error when a FishR number contains letters.
  ///
  /// In en, this message translates to:
  /// **'FishR numbers are digits only'**
  String get validatorFishrDigitsOnly;

  /// Title of the vessel profile screen.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profileTitle;

  /// Tooltip for editing the vessel profile.
  ///
  /// In en, this message translates to:
  /// **'Edit profile'**
  String get profileEdit;

  /// Confirmation shown after saving profile changes.
  ///
  /// In en, this message translates to:
  /// **'Profile updated'**
  String get profileUpdated;

  /// Fallback when the skipper has no saved name.
  ///
  /// In en, this message translates to:
  /// **'No name set'**
  String get profileNoName;

  /// Label for the saved boat name on the profile.
  ///
  /// In en, this message translates to:
  /// **'Boat name'**
  String get profileBoatName;

  /// Label for the automatically generated vessel identifier.
  ///
  /// In en, this message translates to:
  /// **'Vessel ID'**
  String get profileVesselId;

  /// Heading above application settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;

  /// Setting that enables the dark color theme.
  ///
  /// In en, this message translates to:
  /// **'Dark mode'**
  String get darkMode;

  /// Cancels the current edit or dialog.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get actionCancel;

  /// Saves edits to the vessel profile.
  ///
  /// In en, this message translates to:
  /// **'Save changes'**
  String get actionSaveChanges;

  /// Warning shown before saving edited identity details.
  ///
  /// In en, this message translates to:
  /// **'Editing your details resets your trust tier to self-declared. A responder will need to re-confirm your identity.'**
  String get profileEditTrustNotice;

  /// Signs the current identity out of this device.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get logoutAction;

  /// Confirmation shown before logging out. Keep AqOne and SOS untranslated.
  ///
  /// In en, this message translates to:
  /// **'You will need to register again to use AqOne. Your SOS history on this device will be kept.'**
  String get logoutConfirmation;

  /// Error shown when a profile photo cannot be saved.
  ///
  /// In en, this message translates to:
  /// **'Could not update your profile photo.'**
  String get avatarUpdateError;

  /// Profile photo option that opens the camera.
  ///
  /// In en, this message translates to:
  /// **'Take a photo'**
  String get avatarTakePhoto;

  /// Profile photo option that opens the image gallery.
  ///
  /// In en, this message translates to:
  /// **'Choose from gallery'**
  String get avatarChooseGallery;

  /// Profile photo option that deletes the current picture.
  ///
  /// In en, this message translates to:
  /// **'Remove photo'**
  String get avatarRemovePhoto;

  /// SAFETY CRITICAL. Responder status code 1 of 5 (docs/13_RESPONDER_LOOP.md), shown in the responder dialog once a dispatcher has acknowledged the SOS. Means only that the call was seen, not that help has left yet.
  ///
  /// In en, this message translates to:
  /// **'MDRRMO has your call'**
  String get responderStatusReceived;

  /// SAFETY CRITICAL. Responder status code 2 of 5. A rescue boat has actually left to respond.
  ///
  /// In en, this message translates to:
  /// **'Rescue boat on the way'**
  String get responderStatusDispatched;

  /// SAFETY CRITICAL. Responder status code 3 of 5. Keep 'Coast Guard' as the closest local equivalent term, not a literal dictionary translation.
  ///
  /// In en, this message translates to:
  /// **'Coast Guard notified'**
  String get responderStatusCoastGuard;

  /// SAFETY CRITICAL. Responder status code 4 of 5. Other fishing boats near the distress position have been asked to help.
  ///
  /// In en, this message translates to:
  /// **'Nearby boats alerted'**
  String get responderStatusNearestVessel;

  /// SAFETY CRITICAL. Responder status code 5 of 5. Must not read as help has been cancelled - it is still coming, just later than first said.
  ///
  /// In en, this message translates to:
  /// **'Delayed — still coming'**
  String get responderStatusDelayed;

  /// SAFETY CRITICAL. Button in the responder dialog. One tap tells MDRRMO the fisher received the ETA and the emergency is not over.
  ///
  /// In en, this message translates to:
  /// **'Still in danger'**
  String get responderReplyStillInDanger;

  /// SAFETY CRITICAL. Button in the responder dialog. Tapping this leads to a confirmation before it is sent, because it tells MDRRMO to stand the rescue down.
  ///
  /// In en, this message translates to:
  /// **'Safe now'**
  String get responderReplySafeNow;

  /// SAFETY CRITICAL. Confirmation text shown before sending 'Safe now', since it can redirect a rescue already underway.
  ///
  /// In en, this message translates to:
  /// **'This tells MDRRMO you no longer need rescue, and they may send help elsewhere instead. Only confirm if you are actually safe.'**
  String get responderReplyConfirmBody;

  /// SAFETY CRITICAL. Confirms the 'Safe now' reply after the warning text. Must read as a deliberate, informed choice, not a casual OK.
  ///
  /// In en, this message translates to:
  /// **'Yes, I\'m safe'**
  String get responderReplyConfirmConfirm;

  /// Shown after the fisher taps Still in danger and the reply has been recorded (sent or queued).
  ///
  /// In en, this message translates to:
  /// **'MDRRMO knows you are still waiting for help.'**
  String get responderReplySentStillInDanger;

  /// Shown after the fisher confirms Safe now and the reply has been recorded (sent or queued).
  ///
  /// In en, this message translates to:
  /// **'MDRRMO has been told you are safe.'**
  String get responderReplySentSafeNow;

  /// SAFETY CRITICAL. Shown when a reply could not reach the backend immediately and is saved locally to retry later. Must not imply the reply already reached MDRRMO.
  ///
  /// In en, this message translates to:
  /// **'Not sent yet — will send automatically once you have a connection.'**
  String get responderReplyPending;

  /// Caption under a nearby-boat chat message this handset sent while not connected to the Aquan hub WiFi. The line is saved on this phone only and has not been put on the wire yet - see docs/05_PUBLIC_API.md.
  ///
  /// In en, this message translates to:
  /// **'Queued'**
  String get chatStatusQueued;

  /// Caption under a nearby-boat chat message this handset wrote to the hub's WebSocket. The hub protocol has no delivery receipt, so this only means the phone put the line on the wire - not that the hub, another boat, or shore received it.
  ///
  /// In en, this message translates to:
  /// **'Sent'**
  String get chatStatusSent;

  /// Caption under a nearby-boat chat message once the cloud backend has confirmed it stored the line (HTTP 201 from POST /api/mesh/chat). Distinct from chatStatusSent, which has no such confirmation.
  ///
  /// In en, this message translates to:
  /// **'Synced'**
  String get chatStatusSynced;

  /// Live character counter under the chat compose box, shown before the fisher sends so the 50-character limit is visible ahead of time, not just after a rejection.
  ///
  /// In en, this message translates to:
  /// **'{used}/{max}'**
  String chatCharacterLimitLabel(int used, int max);

  /// SAFETY CRITICAL. Heading on the neutral squall banner shown whenever the backend cannot confirm a squall status - stale data, too few reporting buoys, or another quality problem, not staleness alone. Must read as neutral/informational, never alarming - it replaces the RETURN NOW/watch banner, which never appears in this state, and it must not be softened into implying the sea is calm.
  ///
  /// In en, this message translates to:
  /// **'Squall nowcast: status unavailable'**
  String get squallStaleTitle;

  /// SAFETY CRITICAL. Body text on the neutral squall notice when the backend supplied a last-reading time. {age} is a short duration like "3h" or "45 min", already formatted - do not add units around the placeholder.
  ///
  /// In en, this message translates to:
  /// **'Last known reading {age} ago. Not showing a squall status right now.'**
  String squallStaleBodyWithAge(String age);

  /// SAFETY CRITICAL. Body text on the neutral squall notice when no last-reading time is available at all.
  ///
  /// In en, this message translates to:
  /// **'Not showing a squall status right now.'**
  String get squallStaleBodyNoAge;

  /// Section title for the fishing weather window summary card.
  ///
  /// In en, this message translates to:
  /// **'Fishing weather window'**
  String get weatherWindowTitle;

  /// SAFETY CRITICAL. Status badge when current forecast conditions are below caution thresholds.
  ///
  /// In en, this message translates to:
  /// **'Lower forecast risk'**
  String get weatherWindowLowerRisk;

  /// SAFETY CRITICAL. Headline when current conditions or active advisories require caution.
  ///
  /// In en, this message translates to:
  /// **'Conditions need caution now'**
  String get weatherWindowCautionNow;

  /// SAFETY CRITICAL. Subtitle under caution headline. Must remind fishers to check advisories.
  ///
  /// In en, this message translates to:
  /// **'Prepare and check advisories.'**
  String get weatherWindowCautionSubtitle;

  /// SAFETY CRITICAL. Headline when current conditions or official warnings are dangerous.
  ///
  /// In en, this message translates to:
  /// **'High-risk conditions now'**
  String get weatherWindowDangerNow;

  /// SAFETY CRITICAL. Subtitle under high-risk headline. Keep MDRRMO untranslated.
  ///
  /// In en, this message translates to:
  /// **'Follow MDRRMO guidance.'**
  String get weatherWindowDangerSubtitle;

  /// SAFETY CRITICAL. Main countdown line for positive fishing weather window. {duration} is formatted duration.
  ///
  /// In en, this message translates to:
  /// **'Conditions may worsen in about {duration}'**
  String weatherWindowWorsenPrefix(String duration);

  /// Used when forecast deterioration is expected in less than one hour.
  ///
  /// In en, this message translates to:
  /// **'within an hour'**
  String get weatherWindowWithinHour;

  /// Formatted duration with days and hours.
  ///
  /// In en, this message translates to:
  /// **'{days, plural, =1{1 day} other{{days} days}} {hours, plural, =1{1 hour} other{{hours} hours}}'**
  String weatherWindowDurationDaysHours(int days, int hours);

  /// Formatted duration with days only.
  ///
  /// In en, this message translates to:
  /// **'{days, plural, =1{1 day} other{{days} days}}'**
  String weatherWindowDurationDaysOnly(int days);

  /// Formatted duration with hours only.
  ///
  /// In en, this message translates to:
  /// **'{hours, plural, =1{1 hour} other{{hours} hours}}'**
  String weatherWindowDurationHoursOnly(int hours);

  /// Upcoming deterioration details with time and cause. {time} is formatted time, {cause} is localized reason.
  ///
  /// In en, this message translates to:
  /// **'From {time}: {cause}'**
  String weatherWindowUpcoming(String time, String cause);

  /// SAFETY CRITICAL. Reminder that the forecast window ends when conditions worsen and does not include travel back to shore.
  ///
  /// In en, this message translates to:
  /// **'Does not include return travel or preparation time.'**
  String get weatherWindowReturnTravelDisclaimer;

  /// Headline when no caution/danger thresholds are crossed within the near-term forecast horizon.
  ///
  /// In en, this message translates to:
  /// **'No worsening forecast through {time}'**
  String weatherWindowNoWorsening(String time);

  /// Subtitle when no deterioration is forecast in the confident horizon.
  ///
  /// In en, this message translates to:
  /// **'Near-term forecast remains low risk.'**
  String get weatherWindowNoWorseningSubtitle;

  /// Shown when future hazard is known but earlier hourly intervals have gaps.
  ///
  /// In en, this message translates to:
  /// **'Earlier conditions unavailable'**
  String get weatherWindowEarlierMissing;

  /// Subtitle explaining why countdown is not shown when data gaps exist.
  ///
  /// In en, this message translates to:
  /// **'Earlier hourly conditions unavailable — continuous window cannot be calculated.'**
  String get weatherWindowEarlierMissingSubtitle;

  /// Shown when only daily forecast is available without hourly data.
  ///
  /// In en, this message translates to:
  /// **'Hourly estimate unavailable from daily forecast'**
  String get weatherWindowDailyOnly;

  /// Shown when daily forecast indicates higher risk on a specific day but hourly breakdown is missing.
  ///
  /// In en, this message translates to:
  /// **'Higher risk forecast on {day}; hourly estimate unavailable'**
  String weatherWindowDailyAdverse(String day);

  /// Shown when hourly wave, wind, or condition data is missing during scan.
  ///
  /// In en, this message translates to:
  /// **'Forecast estimate incomplete'**
  String get weatherWindowIncomplete;

  /// Subtitle explaining missing data with refresh prompt.
  ///
  /// In en, this message translates to:
  /// **'Missing hourly wave or wind data. Tap to refresh.'**
  String get weatherWindowIncompleteSubtitle;

  /// Headline when forecast is older than 30 minutes.
  ///
  /// In en, this message translates to:
  /// **'Forecast refresh needed'**
  String get weatherWindowRefreshNeeded;

  /// Subtitle for stale forecast beyond refresh threshold.
  ///
  /// In en, this message translates to:
  /// **'Forecast is over 30 minutes old. Tap to refresh.'**
  String get weatherWindowRefreshNeededSubtitle;

  /// Headline when forecast is older than 12 hours.
  ///
  /// In en, this message translates to:
  /// **'Forecast expired'**
  String get weatherWindowExpired;

  /// Subtitle when cache has expired.
  ///
  /// In en, this message translates to:
  /// **'Cached forecast is over 12 hours old. Refresh needed.'**
  String get weatherWindowExpiredSubtitle;

  /// Headline when forecast timestamp is in the future or clock is skewed.
  ///
  /// In en, this message translates to:
  /// **'Forecast timestamp unavailable'**
  String get weatherWindowClockSkew;

  /// Subtitle for clock skew issue.
  ///
  /// In en, this message translates to:
  /// **'Device clock or forecast timestamp is out of sync.'**
  String get weatherWindowClockSkewSubtitle;

  /// Headline when no forecast data is available.
  ///
  /// In en, this message translates to:
  /// **'Weather window unavailable'**
  String get weatherWindowNoForecast;

  /// Subtitle when forecast is null or empty.
  ///
  /// In en, this message translates to:
  /// **'No forecast data available. Tap to load.'**
  String get weatherWindowNoForecastSubtitle;

  /// Metadata line showing the forecast location.
  ///
  /// In en, this message translates to:
  /// **'Forecast location: {location}'**
  String weatherWindowLocationLabel(String location);

  /// Reason: wind gusts meeting caution or danger threshold.
  ///
  /// In en, this message translates to:
  /// **'stronger winds'**
  String get deteriorationReasonStrongWinds;

  /// Reason: wave height meeting caution or danger threshold.
  ///
  /// In en, this message translates to:
  /// **'higher waves'**
  String get deteriorationReasonHighWaves;

  /// Reason: thunderstorm condition.
  ///
  /// In en, this message translates to:
  /// **'thunderstorms'**
  String get deteriorationReasonThunderstorm;

  /// Reason: heavy rain condition.
  ///
  /// In en, this message translates to:
  /// **'heavy rain'**
  String get deteriorationReasonHeavyRain;

  /// Reason: fog or poor visibility.
  ///
  /// In en, this message translates to:
  /// **'poor visibility'**
  String get deteriorationReasonPoorVisibility;

  /// Reason: daily rainfall threshold exceeded.
  ///
  /// In en, this message translates to:
  /// **'heavy daily rain'**
  String get deteriorationReasonDailyRain;

  /// Reason: MDRRMO sea condition set to caution.
  ///
  /// In en, this message translates to:
  /// **'official caution'**
  String get deteriorationReasonOfficialCaution;

  /// Reason: MDRRMO sea condition set to not advised.
  ///
  /// In en, this message translates to:
  /// **'official warning: not advised'**
  String get deteriorationReasonOfficialDanger;

  /// Reason: squall watch alert active.
  ///
  /// In en, this message translates to:
  /// **'squall watch'**
  String get deteriorationReasonSquallWatch;

  /// Reason: squall return now alert active.
  ///
  /// In en, this message translates to:
  /// **'squall danger: return now'**
  String get deteriorationReasonSquallDanger;

  /// Loading indicator text on weather card.
  ///
  /// In en, this message translates to:
  /// **'Loading weather…'**
  String get weatherLoading;

  /// Shown when weather reading is unavailable.
  ///
  /// In en, this message translates to:
  /// **'Weather unavailable'**
  String get weatherUnavailable;

  /// Button label to retry fetching weather.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get weatherRetry;

  /// Shown when forecast is using current device position.
  ///
  /// In en, this message translates to:
  /// **'your position'**
  String get weatherLocationYourPosition;

  /// Shown when forecast is using default municipal coordinates.
  ///
  /// In en, this message translates to:
  /// **'Aklan (default)'**
  String get weatherLocationDefault;

  /// Shown when the fisher cancels the emergency SOS countdown before dispatch.
  ///
  /// In en, this message translates to:
  /// **'SOS cancelled. Nothing was sent.'**
  String get sosCancelledNothingSent;

  /// Shown when attempting to send an SOS without completing vessel setup.
  ///
  /// In en, this message translates to:
  /// **'Finish setting up your boat before sending an SOS.'**
  String get sosSetupBoatRequired;

  /// SAFETY CRITICAL. Shown in the responder countdown when the estimated arrival time has passed but rescue is still en route.
  ///
  /// In en, this message translates to:
  /// **'Delayed — still on the way'**
  String get responderDelayedStillOnWay;

  /// System-notification title when the MDRRMO acknowledges an SOS with an ETA.
  ///
  /// In en, this message translates to:
  /// **'Help is coming'**
  String get rescueNotifTitle;

  /// SAFETY CRITICAL. System-notification body carrying the MDRRMO's arrival estimate, pluralized.
  ///
  /// In en, this message translates to:
  /// **'Rescue boat arriving in {minutes, plural, =1{1 minute} other{{minutes} minutes}}'**
  String rescueNotifBodyMinutes(int minutes);

  /// SAFETY CRITICAL. System-notification body when the ETA is under a minute away.
  ///
  /// In en, this message translates to:
  /// **'Rescue boat arriving any moment now.'**
  String get rescueNotifBodySoon;

  /// SAFETY CRITICAL. System-notification body shown after the promised arrival time has passed; rescue is still en route.
  ///
  /// In en, this message translates to:
  /// **'The rescue boat is delayed but still coming. Stay with your boat.'**
  String get rescueNotifBodyDelayed;

  /// Heading (and system-notification title) shown when the MDRRMO has closed this SOS. Rescue is over - the ETA no longer counts down.
  ///
  /// In en, this message translates to:
  /// **'Incident resolved'**
  String get resolvedTitle;

  /// SAFETY CRITICAL. System-notification body when the MDRRMO resolves the incident. Must not imply rescue is still coming, and must point to raising a new SOS if help is still needed.
  ///
  /// In en, this message translates to:
  /// **'MDRRMO has closed this incident. If you still need help, raise a new SOS.'**
  String get resolvedNotifBody;

  /// SAFETY CRITICAL. Line under the Incident resolved heading on the SOS status card. Must not read as 'stay put, help is coming'.
  ///
  /// In en, this message translates to:
  /// **'MDRRMO has closed this incident. Rescue is no longer needed.'**
  String get resolvedDescription;

  /// AppBar title on the avatar crop screen.
  ///
  /// In en, this message translates to:
  /// **'Position your photo'**
  String get cropPhotoTitle;

  /// Hint text under the crop circle on the avatar crop screen.
  ///
  /// In en, this message translates to:
  /// **'Drag to move · pinch to zoom'**
  String get cropPhotoHint;

  /// Button to confirm the cropped avatar photo.
  ///
  /// In en, this message translates to:
  /// **'Use photo'**
  String get cropPhotoUse;

  /// Error shown when the image processing fails on the crop screen.
  ///
  /// In en, this message translates to:
  /// **'That image could not be processed.'**
  String get cropPhotoError;

  /// Dialog title when resetting the trip checklist.
  ///
  /// In en, this message translates to:
  /// **'Start a new trip?'**
  String get checklistNewTripTitle;

  /// Dialog body explaining the trip checklist reset.
  ///
  /// In en, this message translates to:
  /// **'This unchecks everything on the list so you can go through your gear again. Your items stay - nothing is deleted.'**
  String get checklistNewTripBody;

  /// Confirm button in the new-trip dialog.
  ///
  /// In en, this message translates to:
  /// **'Start new trip'**
  String get checklistStartNewTrip;

  /// SnackBar confirmation after checklist reset.
  ///
  /// In en, this message translates to:
  /// **'Checklist reset for the next trip.'**
  String get checklistResetSnackBar;

  /// AppBar title of the checklist screen.
  ///
  /// In en, this message translates to:
  /// **'Trip checklist'**
  String get checklistTripTitle;

  /// AppBar action button to start a new trip.
  ///
  /// In en, this message translates to:
  /// **'New trip'**
  String get checklistNewTripButton;

  /// Label showing checklist progress. {done} and {total} are integers.
  ///
  /// In en, this message translates to:
  /// **'{done} of {total} packed'**
  String checklistPackedLabel(int done, int total);

  /// Empty state text when the checklist has no items.
  ///
  /// In en, this message translates to:
  /// **'No checklist items yet.'**
  String get checklistEmpty;

  /// Hint text in the add-item text field.
  ///
  /// In en, this message translates to:
  /// **'Add an item'**
  String get checklistAddItem;

  /// SAFETY CRITICAL. Button text on the squall full-screen alert and home-page squall banner. The fisher taps this to acknowledge the squall warning.
  ///
  /// In en, this message translates to:
  /// **'I\'m heading back'**
  String get squallAckButton;

  /// Disclaimer under the squall alert. Must not overstate confidence.
  ///
  /// In en, this message translates to:
  /// **'This model is still being calibrated on simulated data. Use your own judgement.'**
  String get squallModelDisclaimer;

  /// Note under the squall acknowledge button.
  ///
  /// In en, this message translates to:
  /// **'The warning stays on your screen until the squall passes.'**
  String get squallWarningStays;

  /// SnackBar shown when the phone disconnects from a buoy WiFi. {ssid} is the network name.
  ///
  /// In en, this message translates to:
  /// **'Disconnected from {ssid}'**
  String buoyDisconnectSnack(String ssid);

  /// SnackBar shown when the phone connects to a buoy WiFi. {ssid} is the network name.
  ///
  /// In en, this message translates to:
  /// **'Connected to {ssid}'**
  String buoyConnectSnack(String ssid);

  /// Dismiss button on informational dialogs.
  ///
  /// In en, this message translates to:
  /// **'Got it'**
  String get gotItButton;

  /// AppBar title of the buoy connection screen. Shows the phone's real Wi-Fi network and the live buoy link.
  ///
  /// In en, this message translates to:
  /// **'Buoy Wi-Fi'**
  String get wifiTitle;

  /// Shown on the buoy connection screen when the phone is on no Wi-Fi network.
  ///
  /// In en, this message translates to:
  /// **'Not connected to Wi-Fi'**
  String get wifiNotConnected;

  /// Guidance on the buoy connection screen when the phone is on no Wi-Fi network. The app cannot join networks itself.
  ///
  /// In en, this message translates to:
  /// **'Join a buoy network in the phone\'s Wi-Fi settings, then return here.'**
  String get wifiJoinHint;

  /// Tooltip for the re-center map button on the Venture screen.
  ///
  /// In en, this message translates to:
  /// **'My location'**
  String get myLocationTooltip;

  /// Tooltip for the checklist button on the Venture action rail.
  ///
  /// In en, this message translates to:
  /// **'Trip checklist'**
  String get tripChecklistTooltip;

  /// Tooltip for the chat button on the Venture action rail.
  ///
  /// In en, this message translates to:
  /// **'Chat with nearby boats'**
  String get chatWithBoatsTooltip;

  /// Hint text in the SOS free-text note field.
  ///
  /// In en, this message translates to:
  /// **'Describe what is wrong'**
  String get sosDescribeWrong;

  /// SAFETY CRITICAL. Label above the countdown timer in the responder ETA dialog when the ETA has passed.
  ///
  /// In en, this message translates to:
  /// **'ARRIVAL OVERDUE'**
  String get etaArrivalOverdue;

  /// SAFETY CRITICAL. Label above the countdown timer in the responder ETA dialog.
  ///
  /// In en, this message translates to:
  /// **'ARRIVING IN'**
  String get etaArrivingIn;

  /// SAFETY CRITICAL. Safety reminder shown below the responder reply section.
  ///
  /// In en, this message translates to:
  /// **'Stay with your boat if it is still afloat. It is easier to spot than a person in the water.'**
  String get stayWithBoat;

  /// Button to dismiss the responder ETA dialog.
  ///
  /// In en, this message translates to:
  /// **'Understood'**
  String get understoodButton;

  /// Hint text in the chat compose field.
  ///
  /// In en, this message translates to:
  /// **'Type a message…'**
  String get chatHint;

  /// Display label for WeatherCondition.sunny. Must go through AppLocalizations, not remain as a const on the enum.
  ///
  /// In en, this message translates to:
  /// **'Sunny & Clear'**
  String get weatherConditionSunny;

  /// Display label for WeatherCondition.partlyCloudy.
  ///
  /// In en, this message translates to:
  /// **'Partly Cloudy'**
  String get weatherConditionPartlyCloudy;

  /// Display label for WeatherCondition.overcast.
  ///
  /// In en, this message translates to:
  /// **'Overcast'**
  String get weatherConditionOvercast;

  /// Display label for WeatherCondition.foggy.
  ///
  /// In en, this message translates to:
  /// **'Foggy'**
  String get weatherConditionFoggy;

  /// Display label for WeatherCondition.drizzle.
  ///
  /// In en, this message translates to:
  /// **'Light Drizzle'**
  String get weatherConditionDrizzle;

  /// Display label for WeatherCondition.rainy.
  ///
  /// In en, this message translates to:
  /// **'Rainy'**
  String get weatherConditionRainy;

  /// Display label for WeatherCondition.heavyRain.
  ///
  /// In en, this message translates to:
  /// **'Heavy Rain'**
  String get weatherConditionHeavyRain;

  /// Display label for WeatherCondition.showers.
  ///
  /// In en, this message translates to:
  /// **'Showers'**
  String get weatherConditionShowers;

  /// Display label for WeatherCondition.thunderstorm.
  ///
  /// In en, this message translates to:
  /// **'Thunderstorm'**
  String get weatherConditionThunderstorm;

  /// Display label for WeatherCondition.severeThunderstorm.
  ///
  /// In en, this message translates to:
  /// **'Severe Storm'**
  String get weatherConditionSevereStorm;

  /// Display label for WeatherCondition.calm.
  ///
  /// In en, this message translates to:
  /// **'Sunny & Calm'**
  String get weatherConditionCalm;

  /// Small chip label on the sea condition banner when data is older than the freshness threshold.
  ///
  /// In en, this message translates to:
  /// **'may be outdated'**
  String get seaConditionStaleLabel;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['akl', 'en', 'fil'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'akl':
      return AppLocalizationsAkl();
    case 'en':
      return AppLocalizationsEn();
    case 'fil':
      return AppLocalizationsFil();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}

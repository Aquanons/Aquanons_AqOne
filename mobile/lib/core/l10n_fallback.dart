import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

/// Locales the app ships translations for, in picker order.
///
/// `fil` rather than `tl`: `flutter_localizations` ships
/// `GlobalMaterialLocalizations` for `fil` and not for `tl`, and listing a
/// locale the global delegates cannot load throws
/// "No MaterialLocalizations found" the first time any Material widget with
/// built-in copy is built - a date picker, a text-selection menu, a tooltip.
const List<Locale> kSupportedLocales = <Locale>[
  Locale('akl'),
  Locale('fil'),
  Locale('en'),
];

/// The language a fresh install runs in, whatever the phone is set to.
///
/// The app is made for the fishermen of New Washington, whose first language
/// is Aklanon; the device language is deliberately never consulted
/// (docs/22 §2, plan 70 D2).
const Locale kDefaultLocale = Locale('akl');

/// Aklanon (`akl`) has no CLDR data in `flutter_localizations`, so the global
/// delegates reject it. These fallbacks claim every locale and load the
/// Tagalog implementations instead - the closest language Flutter ships
/// (docs/22 §4.2, plan 70 D3).
///
/// They must be listed *after* the global delegates: Flutter resolves
/// delegates in order and takes the first that reports `isSupported`, so
/// `en` and `fil` still get their real localizations and only `akl` reaches
/// these. Our own `AppLocalizations` resolves `akl` properly - the fallback
/// only affects Flutter's built-in widget chrome.
const List<LocalizationsDelegate<dynamic>> kFallbackDelegates =
    <LocalizationsDelegate<dynamic>>[
  _FallbackMaterialDelegate(),
  _FallbackCupertinoDelegate(),
  _FallbackWidgetsDelegate(),
];

const Locale _chromeLocale = Locale('fil');

class _FallbackMaterialDelegate
    extends LocalizationsDelegate<MaterialLocalizations> {
  const _FallbackMaterialDelegate();

  @override
  bool isSupported(Locale locale) => true;

  @override
  Future<MaterialLocalizations> load(Locale locale) =>
      GlobalMaterialLocalizations.delegate.load(_chromeLocale);

  @override
  bool shouldReload(_FallbackMaterialDelegate old) => false;
}

class _FallbackCupertinoDelegate
    extends LocalizationsDelegate<CupertinoLocalizations> {
  const _FallbackCupertinoDelegate();

  @override
  bool isSupported(Locale locale) => true;

  @override
  Future<CupertinoLocalizations> load(Locale locale) =>
      GlobalCupertinoLocalizations.delegate.load(_chromeLocale);

  @override
  bool shouldReload(_FallbackCupertinoDelegate old) => false;
}

class _FallbackWidgetsDelegate
    extends LocalizationsDelegate<WidgetsLocalizations> {
  const _FallbackWidgetsDelegate();

  @override
  bool isSupported(Locale locale) => true;

  @override
  Future<WidgetsLocalizations> load(Locale locale) =>
      GlobalWidgetsLocalizations.delegate.load(_chromeLocale);

  @override
  bool shouldReload(_FallbackWidgetsDelegate old) => false;
}

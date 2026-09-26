import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import '../core/locale_controller.dart';
import '../core/tokens.dart';
import '../core/validators.dart';
import '../data/identity_store.dart';
import '../models/license_type.dart';
import '../models/trust_tier.dart';
import 'info_page.dart';
import '../services/sos_foreground.dart';
import 'widgets/language_picker.dart';

const Color _brandPrimary = Color(0xFF0F69C9);
const Color _brandDeepDark = Color(0xFFBFE3FF);
const Color _authTextDark = Color(0xFFF0F4F8);
const Color _authLabelLight = Color(0xFF4A6B82);
const Color _authLabelDark = Color(0xFFB9CBD8);
const Color _authSubtitleDark = Color(0xFF082B45);
const Color _authHintDark = Color(0xFF8CA3B5);
const Color _authFillDark = Color(0xFF334155);
const Color _noticeBgLight = Color(0xFFFFF4E0);
const Color _noticeBgDark = Color(0xFF3A2E12);
const Color _noticeFgLight = Color(0xFF8A5A12);
const Color _noticeFgDark = Color(0xFFF2C572);

/// Registration for a vessel.
///
/// This screen collects a claim, it does not verify one. There is no public
/// BFAR or LGU lookup to check a number against, and the app is built to work
/// with no internet, so the handset can only check that what was typed has a
/// plausible shape. The copy here says so plainly rather than implying a
/// check that never happens.
///
/// Nothing on this screen blocks the SOS button. The registration number is
/// optional by design - an unregistered fisherman in trouble still needs the
/// app to work.
class OnboardingPage extends StatefulWidget {
  const OnboardingPage({
    super.key,
    required this.identity,
    required this.onReady,
    this.initialIdentity,
    this.localeController,
  });

  final IdentityStore identity;
  final VoidCallback onReady;
  final VesselIdentity? initialIdentity;

  /// Shown as a segmented picker above the form. This is the first screen a
  /// new user ever sees, so it is the only place the language choice is
  /// offered before any other text has to be understood.
  final LocaleController? localeController;

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _name = TextEditingController();
  final TextEditingController _boat = TextEditingController();
  final TextEditingController _license = TextEditingController();
  final TextEditingController _phone = TextEditingController();

  LicenseType _licenseType = LicenseType.none;
  bool _saving = false;
  String? _error;
  bool _rememberMe = true;

  bool get _isReturning {
    final boat = widget.initialIdentity?.boat;
    return boat != null && boat.trim().isNotEmpty;
  }

  @override
  void initState() {
    super.initState();
    final existing = widget.initialIdentity;
    if (existing != null) {
      _name.text = existing.skipperName;
      _boat.text = existing.boat;
      _license.text = existing.licenseNumber;
      _phone.text = existing.phone;
      _licenseType = existing.licenseType;
    }
    _loadRememberMe();
  }

  Future<void> _loadRememberMe() async {
    final remembered = await widget.identity.getRememberMe();
    if (!mounted) {
      return;
    }
    setState(() => _rememberMe = remembered);
  }

  @override
  void dispose() {
    _name.dispose();
    _boat.dispose();
    _license.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final t = AppLocalizations.of(context);
    if (_saving) {
      return;
    }
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.identity.ensure(
        boat: _boat.text,
        skipperName: _name.text,
        licenseType: _licenseType,
        licenseNumber: _license.text,
        phone: _phone.text,
      );
      await widget.identity.setRememberMe(_rememberMe);
      if (!mounted) {
        return;
      }
      await _requestBatteryOptimizationExemption(t);
      if (!mounted) {
        return;
      }
      widget.onReady();
    } catch (_) {
      // Never strand the user on a dead button: a failed write has to leave
      // the form usable so they can try again.
      if (!mounted) {
        return;
      }
      setState(() {
        _saving = false;
        _error = t.onboardingSaveError;
      });
    }
  }

  Future<void> _requestBatteryOptimizationExemption(AppLocalizations t) async {
    try {
      final isIgnoring = await SosForeground.isIgnoringBatteryOptimizations();
      if (!isIgnoring && mounted) {
        await showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            title: Text(t.safetyNotice),
            content: Text(t.onboardingBatteryWhy),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: Text(t.actionContinue),
              ),
            ],
          ),
        );
        await SosForeground.requestBatteryExemption();
      }
    } catch (_) {
      // Ignored if unsupported on platform or in tests
    }
  }

  void _openInfo(String title, String body) {
    Navigator.push(
      context,
      MaterialPageRoute<void>(
        builder: (_) => InfoPage(title: title, body: body),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    final isWide = mediaQuery.size.width > 600;
    final tier = widget.initialIdentity?.trustTier;
    final t = AppLocalizations.of(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final palette = AqPalette.of(context);
    const brandDeep = _brandDeepDark;
    const authText = _authTextDark;
    const authLabel = _authLabelDark;
    const authHint = _authHintDark;
    const authFill = _authFillDark;

    return Scaffold(
      backgroundColor: palette.canvas,
      body: Stack(
        children: <Widget>[
          Positioned.fill(
            child: Image.asset(
              'assets/images/background.png',
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: <Color>[
                      Color(0xFF020B20),
                      Color(0xFF062B68),
                      Color(0xFF0750C4),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.12),
              ),
            ),
          ),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 20,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        _Branding(
                          isWide: isWide,
                          mediaQuery: mediaQuery,
                          isDark: isDark,
                          brandDeep: brandDeep,
                        ),
                        if (widget.localeController != null) ...<Widget>[
                          const SizedBox(height: 16),
                          Center(
                            child: LanguageSegmentedPicker(
                              controller: widget.localeController!,
                            ),
                          ),
                        ],
                        const SizedBox(height: 24),
                        Text(
                          _isReturning
                              ? t.onboardingWelcomeBack
                              : t.onboardingRegisterBoat,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.bold,
                            color: brandDeep,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _isReturning
                              ? t.onboardingReturningBody
                              : t.onboardingIntroBody,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: _authSubtitleDark,
                            height: 1.4,
                          ),
                        ),
                        const SizedBox(height: 18),
                        if (tier != null) ...<Widget>[
                          _TierChip(tier: tier, isDark: isDark),
                          const SizedBox(height: 14),
                        ],
                        TextFormField(
                          controller: _name,
                          maxLength: 64,
                          textCapitalization: TextCapitalization.words,
                          textInputAction: TextInputAction.next,
                          style: const TextStyle(
                            color: authText,
                            fontSize: 15,
                          ),
                          decoration: _decoration(
                            t.fieldFullName,
                            Icons.person_outline_rounded,
                            isDark: isDark,
                            authHint: authHint,
                            authFill: authFill,
                            authLabel: authLabel,
                          ),
                          validator: (value) =>
                              Validators.skipperName(value, t),
                        ),
                        const SizedBox(height: 14),
                        TextFormField(
                          controller: _boat,
                          maxLength: 32,
                          textCapitalization: TextCapitalization.characters,
                          textInputAction: TextInputAction.next,
                          style: const TextStyle(
                            color: authText,
                            fontSize: 15,
                          ),
                          decoration: _decoration(
                            t.fieldBoatNameOrRegistration,
                            Icons.sailing_outlined,
                            isDark: isDark,
                            authHint: authHint,
                            authFill: authFill,
                            authLabel: authLabel,
                          ),
                          validator: (value) => Validators.boatName(value, t),
                        ),
                        const SizedBox(height: 14),
                        DropdownButtonFormField<LicenseType>(
                          initialValue: _licenseType,
                          isExpanded: true,
                          style: const TextStyle(
                            color: authText,
                            fontSize: 15,
                          ),
                          decoration: _decoration(
                            t.fieldRegistrationType,
                            Icons.badge_outlined,
                            isDark: isDark,
                            authHint: authHint,
                            authFill: authFill,
                            authLabel: authLabel,
                          ),
                          items: <DropdownMenuItem<LicenseType>>[
                            for (final type in LicenseType.values)
                              DropdownMenuItem<LicenseType>(
                                value: type,
                                child: Text(
                                  type.label(t),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                          ],
                          onChanged: _saving
                              ? null
                              : (value) {
                                  if (value == null) {
                                    return;
                                  }
                                  setState(() {
                                    _licenseType = value;
                                    if (!value.requiresNumber) {
                                      _license.clear();
                                    }
                                  });
                                },
                        ),
                        Padding(
                          padding: const EdgeInsets.only(top: 6, left: 4),
                          child: Text(
                            _licenseType.hint(t),
                            style: const TextStyle(
                              fontSize: 16,
                              color: authLabel,
                              height: 1.3,
                            ),
                          ),
                        ),
                        if (_licenseType.requiresNumber) ...<Widget>[
                          const SizedBox(height: 14),
                          TextFormField(
                            controller: _license,
                            maxLength: 24,
                            textCapitalization: TextCapitalization.characters,
                            textInputAction: TextInputAction.next,
                            keyboardType: _licenseType == LicenseType.fishr
                                ? TextInputType.number
                                : TextInputType.text,
                            style: const TextStyle(
                              color: authText,
                              fontSize: 15,
                            ),
                            decoration: _decoration(
                              t.fieldRegistrationNumber(
                                _licenseType.label(t),
                              ),
                              Icons.confirmation_number_outlined,
                              isDark: isDark,
                              authHint: authHint,
                              authFill: authFill,
                              authLabel: authLabel,
                            ),
                            validator: (value) => Validators.license(
                              value,
                              _licenseType,
                              t,
                            ),
                          ),
                        ],
                        const SizedBox(height: 14),
                        TextFormField(
                          controller: _phone,
                          maxLength: 20,
                          keyboardType: TextInputType.phone,
                          textInputAction: TextInputAction.done,
                          onFieldSubmitted: (_) => _submit(),
                          style: const TextStyle(
                            color: authText,
                            fontSize: 15,
                          ),
                          decoration: _decoration(
                            t.fieldMobileNumber,
                            Icons.phone_iphone_rounded,
                            isDark: isDark,
                            authHint: authHint,
                            authFill: authFill,
                            authLabel: authLabel,
                          ),
                          validator: (value) => Validators.phone(value, t),
                        ),
                        const SizedBox(height: 16),
                        _UnverifiedNotice(isDark: isDark),
                        const SizedBox(height: 4),
                        _RememberMeRow(
                          value: _rememberMe,
                          authText: authText,
                          onChanged: (value) =>
                              setState(() => _rememberMe = value),
                        ),
                        if (_error != null) ...<Widget>[
                          const SizedBox(height: 12),
                          Text(
                            _error!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 13,
                              color: Colors.redAccent,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                        const SizedBox(height: 18),
                        ElevatedButton(
                          onPressed: _saving ? null : _submit,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _brandPrimary,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                            elevation: 2,
                            shadowColor: Colors.black26,
                          ),
                          child: _saving
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                    color: Colors.white,
                                    strokeWidth: 2,
                                  ),
                                )
                              : Text(
                                  t.actionContinue,
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                        ),
                        const SizedBox(height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: <Widget>[
                            Row(
                              children: <Widget>[
                                _FooterIcon(
                                  icon: Icons.help_outline_rounded,
                                  isDark: isDark,
                                  onTap: () => _openInfo(
                                    t.helpSupport,
                                    InfoCopy.help,
                                  ),
                                ),
                                const SizedBox(width: 10),
                                _FooterIcon(
                                  icon: Icons.info_outline_rounded,
                                  isDark: isDark,
                                  onTap: () => _openInfo(
                                    t.aboutAqOne,
                                    InfoCopy.about,
                                  ),
                                ),
                              ],
                            ),
                            GestureDetector(
                              onTap: () => _openInfo(
                                t.safetyNotice,
                                InfoCopy.terms,
                              ),
                              child: Text(
                                t.safetyNotice,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                  color: _brandPrimary,
                                  decoration: TextDecoration.underline,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 18),
                        Column(
                          children: <Widget>[
                            Text(
                              t.agreementPrefix,
                              style: const TextStyle(
                                fontSize: 12,
                                color: authLabel,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Wrap(
                              alignment: WrapAlignment.center,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: <Widget>[
                                GestureDetector(
                                  onTap: () => _openInfo(
                                    t.privacyPolicy,
                                    InfoCopy.privacy,
                                  ),
                                  child: Text(
                                    t.privacyPolicy,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: _brandPrimary,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                                Text(
                                  t.agreementAnd,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: authLabel,
                                  ),
                                ),
                                GestureDetector(
                                  onTap: () => _openInfo(
                                    t.termsOfUse,
                                    InfoCopy.terms,
                                  ),
                                  child: Text(
                                    t.termsOfUse,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: _brandPrimary,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  InputDecoration _decoration(
    String hint,
    IconData icon, {
    required bool isDark,
    required Color authHint,
    required Color authFill,
    required Color authLabel,
  }) {
    return InputDecoration(
      hintText: hint,
      counterText: '',
      hintStyle: TextStyle(color: authHint, fontSize: 14),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 14,
      ),
      filled: true,
      fillColor: authFill.withValues(alpha: isDark ? 0.7 : 0.55),
      prefixIcon: Icon(icon, color: authLabel, size: 20),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(
          color: isDark
              ? Colors.white.withValues(alpha: 0.12)
              : Colors.white.withValues(alpha: 0.6),
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: _brandPrimary, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Colors.redAccent),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Colors.redAccent, width: 1.5),
      ),
    );
  }
}

/// "Remember me" toggle: when on, a returning skipper is dropped straight
/// into the app on next launch instead of re-confirming their details.
class _RememberMeRow extends StatelessWidget {
  const _RememberMeRow({
    required this.value,
    required this.authText,
    required this.onChanged,
  });

  final bool value;
  final Color authText;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => onChanged(!value),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: <Widget>[
            SizedBox(
              width: 22,
              height: 22,
              child: Checkbox(
                value: value,
                onChanged: (v) => onChanged(v ?? true),
                activeColor: _brandPrimary,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
            const SizedBox(width: 10),
            Flexible(
              child: Text(
                t.rememberDevice,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: authText,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Says out loud that nothing typed here is checked.
///
/// Deliberate: claiming "verified fishermen only" would be false, and the
/// first responder to trust that claim would be misled at exactly the wrong
/// moment.
class _UnverifiedNotice extends StatelessWidget {
  const _UnverifiedNotice({required this.isDark});

  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final noticeBg = isDark ? _noticeBgDark : _noticeBgLight;
    final noticeFg = isDark ? _noticeFgDark : _noticeFgLight;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: noticeBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: noticeFg.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.privacy_tip_outlined, size: 18, color: noticeFg),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              t.identityUnverifiedNotice,
              style: TextStyle(
                fontSize: 16,
                color: noticeFg,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Shows the current tier so the skipper knows where they stand.
class _TierChip extends StatelessWidget {
  const _TierChip({required this.tier, required this.isDark});

  final TrustTier tier;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final confirmed = tier == TrustTier.confirmedByResponder;
    final authLabel = isDark ? _authLabelDark : _authLabelLight;
    final color = confirmed ? const Color(0xFF1B7F4B) : authLabel;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isDark
            ? const Color(0xFF1E293B).withValues(alpha: 0.85)
            : Colors.white.withValues(alpha: 0.75),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Icon(
            confirmed ? Icons.verified_rounded : Icons.edit_note_rounded,
            size: 16,
            color: color,
          ),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              tier.label(t),
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Branding extends StatelessWidget {
  const _Branding({
    required this.isWide,
    required this.mediaQuery,
    required this.isDark,
    required this.brandDeep,
  });

  final bool isWide;
  final MediaQueryData mediaQuery;
  final bool isDark;
  final Color brandDeep;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Image.asset(
          'assets/images/aqone_logo.png',
          height: isWide ? 140 : mediaQuery.size.height * 0.18,
          fit: BoxFit.contain,
          errorBuilder: (_, __, ___) => Icon(
            Icons.waves_rounded,
            size: isWide ? 96 : mediaQuery.size.height * 0.10,
            color: isDark ? AqColors.skyAccent : _brandPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Gabay sa Bawat Alon,\nKonektado sa Bawat Layon',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: brandDeep,
            height: 1.25,
          ),
        ),
      ],
    );
  }
}

class _FooterIcon extends StatelessWidget {
  const _FooterIcon({
    required this.icon,
    required this.onTap,
    required this.isDark,
  });

  final IconData icon;
  final VoidCallback onTap;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E293B) : Colors.white,
          shape: BoxShape.circle,
          boxShadow: const <BoxShadow>[
            BoxShadow(
              color: Colors.black12,
              blurRadius: 4,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Center(
          child: Icon(icon, size: 18, color: _brandPrimary),
        ),
      ),
    );
  }
}

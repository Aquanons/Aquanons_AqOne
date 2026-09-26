import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:aqone/l10n/app_localizations.dart';

import '../core/locale_controller.dart';
import '../core/tokens.dart';
import '../core/validators.dart';
import '../data/identity_store.dart';
import '../models/license_type.dart';
import '../models/trust_tier.dart';
import '../services/backend_client.dart';
import 'avatar_crop_page.dart';
import 'enrolment_page.dart';
import 'info_page.dart';
import 'widgets/language_picker.dart';

const Color _brandPrimary = Color(0xFF0F69C9);
const Color _authText = Color(0xFF2C4960);
const Color _authLabel = Color(0xFF4A6B82);
const Color _authHint = Color(0xFF7A97AC);
const Color _authFill = Color(0xFFCFE8F9);
const Color _noticeBg = Color(0xFFFFF4E0);
const Color _noticeFg = Color(0xFF8A5A12);
const Color _dangerRed = Color(0xFFE74C3C);

class ProfilePage extends StatefulWidget {
  const ProfilePage({
    super.key,
    required this.identityStore,
    required this.identity,
    this.backendClient,
    required this.themeMode,
    this.onThemeModeChanged,
    this.localeController,
    required this.onLogout,
    required this.onIdentityUpdated,
    this.onOpenHome,
    this.bottomInset = 0,
  });

  final IdentityStore identityStore;
  final VesselIdentity identity;
  final BackendClient? backendClient;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;

  /// Nullable so widget tests and previews can build a ProfilePage without
  /// standing up shared_preferences. The language row is simply hidden when
  /// it is absent.
  final LocaleController? localeController;

  final VoidCallback onLogout;
  final ValueChanged<VesselIdentity> onIdentityUpdated;
  final VoidCallback? onOpenHome;

  /// Height of the bottom navigation dock. Passed in rather than guessed: the
  /// previous hardcoded `+100` was smaller than the dock on devices with
  /// gesture insets, which left the logout button unreachable at the end of
  /// the scroll.
  final double bottomInset;

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _editing = false;
  bool _saving = false;
  bool _pickingAvatar = false;

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  late TextEditingController _name;
  late TextEditingController _boat;
  late TextEditingController _license;
  late TextEditingController _phone;
  late TextEditingController _shoreContactName;
  late TextEditingController _shoreContactPhone;
  late LicenseType _licenseType;
  bool _silentSos = false;

  @override
  void initState() {
    super.initState();
    _loadSilentSos();
    _name = TextEditingController(text: widget.identity.skipperName);
    _boat = TextEditingController(text: widget.identity.boat);
    _license = TextEditingController(text: widget.identity.licenseNumber);
    _phone = TextEditingController(text: widget.identity.phone);
    _shoreContactName =
        TextEditingController(text: widget.identity.shoreContactName);
    _shoreContactPhone =
        TextEditingController(text: widget.identity.shoreContactPhone);
    _licenseType = widget.identity.licenseType;
  }

  Future<void> _loadSilentSos() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() => _silentSos = prefs.getBool('silent_sos') ?? false);
    }
  }

  Future<void> _onSilentSosChanged(bool value) async {
    setState(() => _silentSos = value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('silent_sos', value);
  }

  @override
  void dispose() {
    _name.dispose();
    _boat.dispose();
    _license.dispose();
    _phone.dispose();
    _shoreContactName.dispose();
    _shoreContactPhone.dispose();
    super.dispose();
  }

  void _startEditing() {
    setState(() {
      _editing = true;
      _name.text = widget.identity.skipperName;
      _boat.text = widget.identity.boat;
      _license.text = widget.identity.licenseNumber;
      _phone.text = widget.identity.phone;
      _shoreContactName.text = widget.identity.shoreContactName;
      _shoreContactPhone.text = widget.identity.shoreContactPhone;
      _licenseType = widget.identity.licenseType;
    });
  }

  void _cancelEditing() {
    setState(() => _editing = false);
  }

  Future<void> _save() async {
    if (_saving || !_formKey.currentState!.validate()) return;
    final t = AppLocalizations.of(context);
    setState(() => _saving = true);
    try {
      final updated = await widget.identityStore.ensure(
        boat: _boat.text,
        skipperName: _name.text,
        licenseType: _licenseType,
        licenseNumber: _license.text,
        phone: _phone.text,
        shoreContactName: _shoreContactName.text,
        shoreContactPhone: _shoreContactPhone.text,
      );
      if (widget.backendClient != null) {
        unawaited(widget.backendClient!.registerVesselProfile(updated));
      }
      if (!mounted) return;
      widget.onIdentityUpdated(updated);
      setState(() => _editing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(t.profileUpdated),
          duration: const Duration(seconds: 2),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
    }
  }

  void _confirmLogout() {
    final t = AppLocalizations.of(context);
    showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(t.logoutAction),
        content: Text(t.logoutConfirmation),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(t.actionCancel),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              widget.onLogout();
            },
            style: TextButton.styleFrom(foregroundColor: _dangerRed),
            child: Text(t.logoutAction),
          ),
        ],
      ),
    );
  }

  Future<void> _changeAvatar() async {
    if (_pickingAvatar || kIsWeb) {
      return;
    }
    final hasPhoto = widget.identity.avatarPath != null &&
        widget.identity.avatarPath!.isNotEmpty;
    final choice = await showModalBottomSheet<_AvatarAction>(
      context: context,
      builder: (ctx) => _AvatarActionSheet(hasPhoto: hasPhoto),
    );
    if (choice == null || !mounted) {
      return;
    }

    setState(() => _pickingAvatar = true);
    final String? previousPath = widget.identity.avatarPath;
    try {
      if (choice == _AvatarAction.remove) {
        final updated = await widget.identityStore.setAvatarPath(null);
        if (!mounted) return;
        widget.onIdentityUpdated(updated);
        await _discardAvatarFile(previousPath);
        return;
      }

      final source = choice == _AvatarAction.camera
          ? ImageSource.camera
          : ImageSource.gallery;
      final picked = await ImagePicker().pickImage(
        source: source,
        // Deliberately generous: this is the crop input, not the stored
        // avatar. Downscaling here would throw away detail the user is about
        // to zoom into.
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 90,
      );
      if (picked == null || !mounted) {
        return;
      }

      final Uint8List? cropped = await Navigator.of(context).push<Uint8List>(
        MaterialPageRoute<Uint8List>(
          builder: (_) => AvatarCropPage(source: File(picked.path)),
        ),
      );
      // Backing out of the cropper cancels the whole change; the old photo
      // stays exactly as it was.
      if (cropped == null || !mounted) {
        return;
      }

      final dir = await getApplicationDocumentsDirectory();
      // Unique filename per upload, and this is load-bearing rather than
      // tidiness. Image keys its resolved stream on the file path, so writing
      // every photo to the same profile_avatar.jpg meant the widget kept the
      // already-decoded old bytes and the new picture never appeared -
      // evicting the cache did not help, because the widget still held the
      // completed stream. A new path forces a genuine re-resolve.
      final savedPath =
          '${dir.path}/profile_avatar_${DateTime.now().millisecondsSinceEpoch}.png';
      await File(savedPath).writeAsBytes(cropped, flush: true);

      final updated = await widget.identityStore.setAvatarPath(savedPath);
      if (!mounted) return;
      widget.onIdentityUpdated(updated);

      // Only after the new path is safely persisted. Deleting first would
      // leave a fisherman with no photo at all if the write failed.
      await _discardAvatarFile(previousPath);
    } catch (_) {
      if (!mounted) return;
      final t = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(t.avatarUpdateError),
          duration: const Duration(seconds: 2),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _pickingAvatar = false);
      }
    }
  }

  /// Removes a superseded avatar from disk and from the image cache.
  ///
  /// Every upload now writes a new file, so without this the documents
  /// directory would accumulate one image per change, on handsets where
  /// storage is often the scarcest resource.
  ///
  /// Failure is swallowed on purpose: a leftover file is untidy, a crash in
  /// the middle of changing a profile photo is not.
  Future<void> _discardAvatarFile(String? path) async {
    if (path == null || path.isEmpty) {
      return;
    }
    try {
      await FileImage(File(path)).evict();
      final File file = File(path);
      if (file.existsSync()) {
        await file.delete();
      }
    } catch (_) {
      // Ignored deliberately - see above.
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

  void _handleBack() {
    if (_editing) {
      _cancelEditing();
      return;
    }
    // onOpenHome is checked FIRST, before Navigator.pop().
    //
    // Profile is a tab inside AppShell's IndexedStack, and AppShell itself sits
    // on a route - so Navigator.canPop() is true here. Popping first therefore
    // tore down the whole shell instead of switching tabs, which read to the
    // user as the back button doing nothing useful. Inside a tabbed shell,
    // "back" means "go to Home".
    if (widget.onOpenHome != null) {
      widget.onOpenHome!();
      return;
    }
    if (Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
    } else if (Navigator.of(context, rootNavigator: true).canPop()) {
      Navigator.of(context, rootNavigator: true).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final identity = widget.identity;
    final t = AppLocalizations.of(context);

    return PopScope(
      // Never let the system back gesture pop the shell from a tab either -
      // onPopInvokedWithResult routes it through _handleBack instead.
      canPop: !_editing &&
          widget.onOpenHome == null &&
          Navigator.of(context).canPop(),
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        _handleBack();
      },
      child: Scaffold(
        backgroundColor: palette.canvas,
        appBar: AppBar(
          backgroundColor: palette.surface,
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: _handleBack,
          ),
          title: Text(
            t.profileTitle,
            style: TextStyle(
              color: palette.primaryText,
              fontWeight: FontWeight.w700,
            ),
          ),
          actions: [
            if (!_editing)
              IconButton(
                icon: const Icon(Icons.edit_rounded, size: 20),
                onPressed: _startEditing,
                tooltip: t.profileEdit,
              ),
          ],
        ),
        body: ListView(
          padding: EdgeInsets.fromLTRB(
            AqSpace.screen,
            AqSpace.lg,
            AqSpace.screen,
            AqSpace.xl + widget.bottomInset,
          ),
          children: <Widget>[
            Center(
              child: GestureDetector(
                onTap: _changeAvatar,
                child: Stack(
                  clipBehavior: Clip.none,
                  children: <Widget>[
                    Container(
                      padding: const EdgeInsets.all(3),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: <Color>[Color(0xFF38BDF8), _brandPrimary],
                        ),
                        boxShadow: <BoxShadow>[
                          BoxShadow(
                            color: _brandPrimary.withValues(alpha: 0.35),
                            blurRadius: 14,
                            offset: const Offset(0, 6),
                          ),
                        ],
                      ),
                      child: ClipOval(
                        child: _hasCustomAvatar
                            ? Image.file(
                                File(identity.avatarPath!),
                                height: 88,
                                width: 88,
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) =>
                                    _avatarFallback(palette),
                              )
                            : Image.asset(
                                'icons/emptyProfile.png',
                                height: 88,
                                width: 88,
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) =>
                                    _avatarFallback(palette),
                              ),
                      ),
                    ),
                    Positioned(
                      right: -2,
                      bottom: -2,
                      child: Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _brandPrimary,
                          border: Border.all(color: palette.canvas, width: 2),
                        ),
                        child: _pickingAvatar
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(
                                Icons.camera_alt_rounded,
                                size: 14,
                                color: Colors.white,
                              ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: AqSpace.md),
            Center(
              child: Text(
                identity.skipperName.isNotEmpty
                    ? identity.skipperName
                    : t.profileNoName,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: palette.primaryText,
                ),
              ),
            ),
            const SizedBox(height: AqSpace.xs),
            Center(
              child: Text(
                identity.boat,
                style: TextStyle(
                  fontSize: 14,
                  color: palette.secondaryText,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: AqSpace.xs),
            Center(child: _TierChip(tier: identity.trustTier)),
            const SizedBox(height: AqSpace.lg),
            if (_editing)
              _buildEditForm(palette)
            else
              _buildInfoSection(palette, identity),
            const SizedBox(height: AqSpace.lg),
            Row(
              children: <Widget>[
                Container(
                  width: 4,
                  height: 18,
                  decoration: BoxDecoration(
                    color: _brandPrimary,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  t.settingsTitle,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: palette.primaryText,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AqSpace.sm),
            _ThemeSwitchTile(
              dark: Theme.of(context).brightness == Brightness.dark,
              onChanged: (dark) => widget.onThemeModeChanged?.call(
                dark ? ThemeMode.dark : ThemeMode.light,
              ),
            ),
            _SilentSosSwitchTile(
              enabled: _silentSos,
              onChanged: _onSilentSosChanged,
            ),
            if (widget.localeController != null)
              LanguageSettingTile(controller: widget.localeController!),
            _SettingsTile(
              icon: Icons.verified_user_outlined,
              label: t.enrolTitle,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => EnrolmentPage(
                      backendClient: widget.backendClient ?? BackendClient(),
                      vesselId: identity.vesselId,
                    ),
                  ),
                );
              },
            ),
            _SettingsTile(
              icon: Icons.info_outline_rounded,
              label: t.aboutAqOne,
              onTap: () => _openInfo(t.aboutAqOne, t.infoAboutBody),
            ),
            _SettingsTile(
              icon: Icons.help_outline_rounded,
              label: t.helpSupport,
              onTap: () => _openInfo(t.helpSupport, t.infoHelpBody),
            ),
            _SettingsTile(
              icon: Icons.shield_outlined,
              label: t.privacyPolicy,
              onTap: () => _openInfo(t.privacyPolicy, t.infoPrivacyBody),
            ),
            _SettingsTile(
              icon: Icons.gavel_rounded,
              label: t.termsOfUse,
              onTap: () => _openInfo(t.termsOfUse, t.infoTermsBody),
            ),
            const SizedBox(height: AqSpace.lg),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _confirmLogout,
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: Text(t.logoutAction),
                style: OutlinedButton.styleFrom(
                  foregroundColor: _dangerRed,
                  side: const BorderSide(color: _dangerRed),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AqRadius.button),
                  ),
                ),
              ),
            ),
            const SizedBox(height: AqSpace.xl),
          ],
        ),
      ),
    );
  }

  bool get _hasCustomAvatar {
    final path = widget.identity.avatarPath;
    return !kIsWeb &&
        path != null &&
        path.isNotEmpty &&
        File(path).existsSync();
  }

  Widget _avatarFallback(AqPalette palette) {
    return Container(
      height: 88,
      width: 88,
      color: palette.surface,
      child: const Icon(
        Icons.person,
        size: 44,
        color: _brandPrimary,
      ),
    );
  }

  Widget _buildInfoSection(AqPalette palette, VesselIdentity identity) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(AqSpace.base),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AqRadius.card),
        border: Border.all(color: palette.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _InfoRow(
            label: t.fieldFullName,
            value: identity.skipperName.isNotEmpty ? identity.skipperName : '-',
          ),
          const SizedBox(height: AqSpace.md),
          _InfoRow(label: t.profileBoatName, value: identity.boat),
          const SizedBox(height: AqSpace.md),
          _InfoRow(
            label: t.fieldRegistrationType,
            value: identity.licenseType.label(t),
          ),
          if (identity.hasLicense) ...<Widget>[
            const SizedBox(height: AqSpace.md),
            _InfoRow(
              label: t.fieldRegistrationNumber(identity.licenseType.label(t)),
              value: identity.licenseNumber,
            ),
          ],
          const SizedBox(height: AqSpace.md),
          _InfoRow(
            label: t.fieldMobileNumber,
            value: identity.phone.isNotEmpty ? identity.phone : '-',
          ),
          const SizedBox(height: AqSpace.md),
          _InfoRow(
            label: t.profileShoreContactName,
            value: identity.shoreContactName.isNotEmpty
                ? identity.shoreContactName
                : '-',
          ),
          const SizedBox(height: AqSpace.md),
          _InfoRow(
            label: t.profileShoreContactPhone,
            value: identity.shoreContactPhone.isNotEmpty
                ? identity.shoreContactPhone
                : '-',
          ),
          const SizedBox(height: AqSpace.md),
          _InfoRow(label: t.profileVesselId, value: identity.vesselId),
        ],
      ),
    );
  }

  Widget _buildEditForm(AqPalette palette) {
    final t = AppLocalizations.of(context);
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(AqSpace.base),
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: BorderRadius.circular(AqRadius.card),
              border: Border.all(color: palette.border),
            ),
            child: Column(
              children: <Widget>[
                TextFormField(
                  controller: _name,
                  maxLength: 64,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.next,
                  style: const TextStyle(color: _authText, fontSize: 15),
                  decoration: _decoration(
                      t.fieldFullName, Icons.person_outline_rounded),
                  validator: (value) => Validators.skipperName(value, t),
                ),
                const SizedBox(height: AqSpace.sm),
                TextFormField(
                  controller: _boat,
                  maxLength: 32,
                  textCapitalization: TextCapitalization.characters,
                  textInputAction: TextInputAction.next,
                  style: const TextStyle(color: _authText, fontSize: 15),
                  decoration: _decoration(
                    t.fieldBoatNameOrRegistration,
                    Icons.sailing_outlined,
                  ),
                  validator: (value) => Validators.boatName(value, t),
                ),
                const SizedBox(height: AqSpace.sm),
                DropdownButtonFormField<LicenseType>(
                  initialValue: _licenseType,
                  isExpanded: true,
                  style: const TextStyle(color: _authText, fontSize: 15),
                  decoration: _decoration(
                      t.fieldRegistrationType, Icons.badge_outlined),
                  items: <DropdownMenuItem<LicenseType>>[
                    for (final type in LicenseType.values)
                      DropdownMenuItem<LicenseType>(
                        value: type,
                        child: Text(type.label(t),
                            overflow: TextOverflow.ellipsis),
                      ),
                  ],
                  onChanged: _saving
                      ? null
                      : (value) {
                          if (value == null) return;
                          setState(() {
                            _licenseType = value;
                            if (!value.requiresNumber) _license.clear();
                          });
                        },
                ),
                Padding(
                  padding: const EdgeInsets.only(top: 4, left: 4),
                  child: Text(
                    _licenseType.hint(t),
                    style: const TextStyle(
                      fontSize: 16,
                      color: _authLabel,
                      height: 1.3,
                    ),
                  ),
                ),
                if (_licenseType.requiresNumber) ...<Widget>[
                  const SizedBox(height: AqSpace.sm),
                  TextFormField(
                    controller: _license,
                    maxLength: 24,
                    textCapitalization: TextCapitalization.characters,
                    textInputAction: TextInputAction.next,
                    keyboardType: _licenseType == LicenseType.fishr
                        ? TextInputType.number
                        : TextInputType.text,
                    style: const TextStyle(color: _authText, fontSize: 15),
                    decoration: _decoration(
                      t.fieldRegistrationNumber(_licenseType.label(t)),
                      Icons.confirmation_number_outlined,
                    ),
                    validator: (value) =>
                        Validators.license(value, _licenseType, t),
                  ),
                ],
                const SizedBox(height: AqSpace.sm),
                TextFormField(
                  controller: _phone,
                  maxLength: 20,
                  keyboardType: TextInputType.phone,
                  textInputAction: TextInputAction.next,
                  style: const TextStyle(color: _authText, fontSize: 15),
                  decoration: _decoration(
                      t.fieldMobileNumber, Icons.phone_iphone_rounded),
                  validator: (value) => Validators.phone(value, t),
                ),
                const SizedBox(height: AqSpace.sm),
                TextFormField(
                  controller: _shoreContactName,
                  maxLength: 64,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.next,
                  style: const TextStyle(color: _authText, fontSize: 15),
                  decoration: _decoration(
                    t.profileShoreContactName,
                    Icons.contact_phone_outlined,
                  ),
                ),
                const SizedBox(height: AqSpace.sm),
                TextFormField(
                  controller: _shoreContactPhone,
                  maxLength: 20,
                  keyboardType: TextInputType.phone,
                  textInputAction: TextInputAction.done,
                  style: const TextStyle(color: _authText, fontSize: 15),
                  decoration: _decoration(
                    t.profileShoreContactPhone,
                    Icons.phone_outlined,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AqSpace.md),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: _noticeBg,
              borderRadius: BorderRadius.circular(AqRadius.small),
              border: Border.all(color: _noticeFg.withValues(alpha: 0.25)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Icon(
                  Icons.privacy_tip_outlined,
                  size: 18,
                  color: _noticeFg,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    t.profileEditTrustNotice,
                    style: const TextStyle(
                      fontSize: 16,
                      color: _noticeFg,
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AqSpace.md),
          Row(
            children: <Widget>[
              Expanded(
                child: OutlinedButton(
                  onPressed: _saving ? null : _cancelEditing,
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AqRadius.button),
                    ),
                  ),
                  child: Text(t.actionCancel),
                ),
              ),
              const SizedBox(width: AqSpace.md),
              Expanded(
                child: ElevatedButton(
                  onPressed: _saving ? null : _save,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _brandPrimary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AqRadius.button),
                    ),
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
                          t.actionSaveChanges,
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  InputDecoration _decoration(String hint, IconData icon) {
    return InputDecoration(
      hintText: hint,
      counterText: '',
      hintStyle: const TextStyle(color: _authHint, fontSize: 14),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      filled: true,
      fillColor: _authFill.withValues(alpha: 0.55),
      prefixIcon: Icon(icon, color: _authLabel, size: 20),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.6)),
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

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: palette.dimText,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w500,
            color: palette.primaryText,
          ),
        ),
      ],
    );
  }
}

class _TierChip extends StatelessWidget {
  const _TierChip({required this.tier});

  final TrustTier tier;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final confirmed = tier == TrustTier.confirmedByResponder;
    final color = confirmed ? const Color(0xFF1B7F4B) : _authLabel;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.75),
        borderRadius: BorderRadius.circular(AqRadius.pill),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(
            confirmed ? Icons.verified_rounded : Icons.edit_note_rounded,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 4),
          Text(
            tier.label(t),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _ThemeSwitchTile extends StatelessWidget {
  const _ThemeSwitchTile({required this.dark, required this.onChanged});

  final bool dark;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: AqSpace.xs),
      child: Material(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AqRadius.standard),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Row(
            children: <Widget>[
              Icon(
                dark ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                size: 20,
                color: palette.secondaryText,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  t.darkMode,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: palette.primaryText,
                  ),
                ),
              ),
              Switch(
                value: dark,
                onChanged: onChanged,
                activeTrackColor: palette.active,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SilentSosSwitchTile extends StatelessWidget {
  const _SilentSosSwitchTile({
    required this.enabled,
    required this.onChanged,
  });

  final bool enabled;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: AqSpace.xs),
      child: Material(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AqRadius.standard),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: <Widget>[
              Icon(
                enabled ? Icons.volume_off_rounded : Icons.volume_up_rounded,
                size: 20,
                color: palette.secondaryText,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      t.settingsSilentSos,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: palette.primaryText,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      t.settingsSilentSosDescription,
                      style: TextStyle(
                        fontSize: 12,
                        color: palette.dimText,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Switch(
                key: const Key('silent_sos_switch'),
                value: enabled,
                onChanged: onChanged,
                activeTrackColor: palette.active,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: AqSpace.xs),
      child: Material(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AqRadius.standard),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AqRadius.standard),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: <Widget>[
                Icon(icon, size: 20, color: palette.secondaryText),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: palette.primaryText,
                    ),
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  size: 20,
                  color: palette.dimText,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

enum _AvatarAction { camera, gallery, remove }

/// Bottom sheet offering camera / gallery / remove for the profile photo.
class _AvatarActionSheet extends StatelessWidget {
  const _AvatarActionSheet({required this.hasPhoto});

  final bool hasPhoto;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: palette.surface,
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(AqRadius.large),
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: palette.border,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            ListTile(
              leading:
                  Icon(Icons.photo_camera_rounded, color: palette.primaryText),
              title: Text(
                t.avatarTakePhoto,
                style: TextStyle(color: palette.primaryText),
              ),
              onTap: () => Navigator.pop(context, _AvatarAction.camera),
            ),
            ListTile(
              leading:
                  Icon(Icons.photo_library_rounded, color: palette.primaryText),
              title: Text(
                t.avatarChooseGallery,
                style: TextStyle(color: palette.primaryText),
              ),
              onTap: () => Navigator.pop(context, _AvatarAction.gallery),
            ),
            if (hasPhoto)
              ListTile(
                leading:
                    const Icon(Icons.delete_outline_rounded, color: _dangerRed),
                title: Text(
                  t.avatarRemovePhoto,
                  style: const TextStyle(color: _dangerRed),
                ),
                onTap: () => Navigator.pop(context, _AvatarAction.remove),
              ),
          ],
        ),
      ),
    );
  }
}

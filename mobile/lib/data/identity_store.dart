import 'dart:math';

import 'package:sqflite/sqflite.dart';

import '../core/config.dart';
import '../core/validators.dart';
import '../models/license_type.dart';
import '../models/trust_tier.dart';
import '../core/field_cipher.dart';
import '../models/text_clamp.dart';
import 'app_database.dart';

/// What this handset claims about itself.
///
/// Every field except [vesselId] and [trustTier] is typed in by the skipper
/// and is unverified. [trustTier] records who, if anyone, has corroborated
/// the rest. See [TrustTier] for why the app never treats this as proof.
class VesselIdentity {
  const VesselIdentity({
    required this.vesselId,
    required this.boat,
    this.skipperName = '',
    this.licenseType = LicenseType.none,
    this.licenseNumber = '',
    this.phone = '',
    this.trustTier = TrustTier.selfDeclared,
    this.avatarPath,
  });

  final String vesselId;
  final String boat;
  final String skipperName;
  final LicenseType licenseType;
  final String licenseNumber;
  final String phone;
  final TrustTier trustTier;

  /// Local filesystem path to the skipper's chosen profile photo, if any.
  /// Never sent anywhere - this is a device-only personalization, not part
  /// of the registration payload.
  final String? avatarPath;

  /// The minimum needed to raise an SOS. Deliberately just an id and a boat
  /// name: a half-finished profile must never stand between someone and the
  /// SOS button.
  bool get isComplete => vesselId.isNotEmpty && boat.isNotEmpty;

  /// Whether the skipper gave a registration number of any kind.
  bool get hasLicense =>
      licenseType.requiresNumber && licenseNumber.isNotEmpty;

  /// Details a dispatcher would want on screen. Sent to the backend once at
  /// registration, not on every SOS - the LoRa packet cannot carry this.
  Map<String, Object?> toRegistrationPayload() => <String, Object?>{
        'v': AqOneConfig.protocolVersion,
        'vessel_id': vesselId,
        'boat': boat,
        'skipper_name': skipperName,
        'license_type': licenseType.wire,
        'license_number': licenseNumber,
        'phone': phone,
        'trust_tier': trustTier.wire,
      };

  VesselIdentity copyWith({
    String? boat,
    String? skipperName,
    LicenseType? licenseType,
    String? licenseNumber,
    String? phone,
    TrustTier? trustTier,
    String? avatarPath,
  }) {
    return VesselIdentity(
      vesselId: vesselId,
      boat: boat ?? this.boat,
      skipperName: skipperName ?? this.skipperName,
      licenseType: licenseType ?? this.licenseType,
      licenseNumber: licenseNumber ?? this.licenseNumber,
      phone: phone ?? this.phone,
      trustTier: trustTier ?? this.trustTier,
      avatarPath: avatarPath ?? this.avatarPath,
    );
  }
}

class IdentityStore {
  IdentityStore(this._db, {FieldCipher? cipher})
      : _cipher = cipher ?? FieldCipher.plaintext();

  final AppDatabase _db;

  /// Encrypts the personal fields only. Injected rather than looked up so
  /// tests and the onboarding path can run without a platform keystore.
  FieldCipher _cipher;

  /// Swapped in once the keystore has been read at startup. Rows written
  /// before that stay plaintext and are re-written encrypted on the next
  /// save - see FieldCipher for why there is no migration sweep.
  void useCipher(FieldCipher cipher) => _cipher = cipher;

  /// Personal data, encrypted at rest when a key is available.
  ///
  /// Deliberately NOT included: vessel_id and boat identify the vessel to
  /// responders and are emergency-critical, license_type and trust_tier are
  /// non-sensitive categories, and avatar_path is an app-private filename
  /// whose image is already excluded from backup. Encrypting the emergency
  /// fields would put a rescue behind a keystore read.
  static const Set<String> _encryptedKeys = <String>{
    _keySkipperName,
    _keyLicenseNumber,
    _keyPhone,
  };

  static const String _keyVesselId = 'vessel_id';
  static const String _keyBoat = 'boat';
  static const String _keySkipperName = 'skipper_name';
  static const String _keyLicenseType = 'license_type';
  static const String _keyLicenseNumber = 'license_number';
  static const String _keyPhone = 'phone';
  static const String _keyTrustTier = 'trust_tier';
  static const String _keyAvatarPath = 'avatar_path';
  static const String _keyRememberMe = 'remember_me';

  Future<VesselIdentity?> read() async {
    final db = await _db.database;
    final rows = await db.query('identity');
    if (rows.isEmpty) {
      return null;
    }
    final values = <String, String>{
      for (final row in rows) row['key'] as String: row['value'] as String,
    };
    for (final String key in _encryptedKeys) {
      final String? stored = values[key];
      if (stored != null) {
        values[key] = await _cipher.decrypt(stored);
      }
    }
    final vesselId = values[_keyVesselId];
    final boat = values[_keyBoat];
    if (vesselId == null || boat == null) {
      return null;
    }
    final avatarPath = values[_keyAvatarPath];
    return VesselIdentity(
      vesselId: vesselId,
      boat: boat,
      skipperName: values[_keySkipperName] ?? '',
      licenseType: LicenseType.fromWire(values[_keyLicenseType]),
      licenseNumber: values[_keyLicenseNumber] ?? '',
      phone: values[_keyPhone] ?? '',
      trustTier: TrustTier.fromWire(values[_keyTrustTier]),
      avatarPath: (avatarPath == null || avatarPath.isEmpty)
          ? null
          : avatarPath,
    );
  }

  /// Whether a returning skipper asked to be dropped straight into the app
  /// on next launch, skipping the "Welcome back" confirmation screen.
  /// Defaults to on: the confirmation screen is friction most returning
  /// users will not want to repeat every time they open the app.
  Future<bool> getRememberMe() async {
    final db = await _db.database;
    final rows = await db.query(
      'identity',
      where: 'key = ?',
      whereArgs: <String>[_keyRememberMe],
      limit: 1,
    );
    if (rows.isEmpty) {
      return true;
    }
    return rows.first['value'] == '1';
  }

  Future<void> setRememberMe(bool value) async {
    final db = await _db.database;
    await db.insert(
      'identity',
      <String, Object?>{
        'key': _keyRememberMe,
        'value': value ? '1' : '0',
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Sets (or, with `null`, clears) the local profile photo path.
  ///
  /// Written directly rather than through [ensure]/`copyWith`, because
  /// `copyWith`'s "null means keep the old value" convention can't express
  /// "the user removed their photo".
  Future<VesselIdentity> setAvatarPath(String? path) async {
    final existing = await read();
    if (existing == null) {
      throw StateError('setAvatarPath called before an identity exists');
    }
    final db = await _db.database;
    if (path == null || path.isEmpty) {
      await db.delete(
        'identity',
        where: 'key = ?',
        whereArgs: <String>[_keyAvatarPath],
      );
    } else {
      await db.insert(
        'identity',
        <String, Object?>{'key': _keyAvatarPath, 'value': path},
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    return VesselIdentity(
      vesselId: existing.vesselId,
      boat: existing.boat,
      skipperName: existing.skipperName,
      licenseType: existing.licenseType,
      licenseNumber: existing.licenseNumber,
      phone: existing.phone,
      trustTier: existing.trustTier,
      avatarPath: (path == null || path.isEmpty) ? null : path,
    );
  }

  /// Creates or updates the local profile.
  ///
  /// The vessel id is reused if one already exists so that reinstalling does
  /// not silently orphan the SOS history on the backend. Note that a
  /// client-generated id is not a ban primitive - a determined abuser can
  /// clear app data and get a fresh one. Making a ban stick needs a
  /// server-issued id and a per-vessel secret; this method is the seam where
  /// that would land.
  Future<VesselIdentity> ensure({
    required String boat,
    String skipperName = '',
    LicenseType licenseType = LicenseType.none,
    String licenseNumber = '',
    String phone = '',
  }) async {
    final existing = await read();
    final identity = VesselIdentity(
      vesselId: existing?.vesselId ?? generateVesselId(),
      boat: _clamp(Validators.normalizeName(boat), AqOneConfig.maxBoatBytes),
      skipperName: _clamp(
        Validators.normalizeName(skipperName),
        AqOneConfig.maxNameLength,
      ),
      licenseType: licenseType,
      licenseNumber: licenseType.requiresNumber
          ? _clamp(
              Validators.normalizeLicense(licenseNumber),
              AqOneConfig.maxLicenseLength,
            )
          : '',
      phone: _clamp(
        Validators.normalizePhone(phone),
        AqOneConfig.maxPhoneLength,
      ),
      // Anything typed on this handset is self-declared, full stop. Only the
      // MDRRMO side can raise this, and only after meeting the vessel.
      trustTier: _preservedTier(existing),
      // A profile photo is unrelated to the declared details being edited
      // here, so it survives an edit untouched.
      avatarPath: existing?.avatarPath,
    );
    await _write(identity);
    return identity;
  }

  Future<void> updateBoat(String boat) async {
    final existing = await read();
    if (existing == null) {
      await ensure(boat: boat);
      return;
    }
    await _write(
      existing.copyWith(
        boat: _clamp(Validators.normalizeName(boat), AqOneConfig.maxBoatBytes),
      ),
    );
  }

  /// Applies a tier granted elsewhere - a responder confirmation coming back
  /// from the backend, or a completed OTP check. Never called with a tier the
  /// handset decided on its own.
  Future<void> applyTrustTier(TrustTier tier) async {
    final existing = await read();
    if (existing == null) {
      return;
    }
    await _write(existing.copyWith(trustTier: tier));
  }

  /// A responder confirmation survives an edit, but any *other* change to the
  /// declared details drops back to self-declared, because the thing that was
  /// confirmed is no longer what is on file.
  static TrustTier _preservedTier(VesselIdentity? existing) {
    return existing?.trustTier == TrustTier.confirmedByResponder
        ? TrustTier.confirmedByResponder
        : TrustTier.selfDeclared;
  }

  Future<void> _write(VesselIdentity identity) async {
    final db = await _db.database;
    final values = <String, String>{
      _keyVesselId: identity.vesselId,
      _keyBoat: identity.boat,
      _keySkipperName: identity.skipperName,
      _keyLicenseType: identity.licenseType.wire,
      _keyLicenseNumber: identity.licenseNumber,
      _keyPhone: identity.phone,
      _keyTrustTier: identity.trustTier.wire,
      if (identity.avatarPath != null && identity.avatarPath!.isNotEmpty)
        _keyAvatarPath: identity.avatarPath!,
    };
    for (final String key in _encryptedKeys) {
      final String? clear = values[key];
      if (clear != null && clear.isNotEmpty) {
        values[key] = await _cipher.encrypt(clear);
      }
    }

    final batch = db.batch();
    values.forEach((key, value) {
      batch.insert(
        'identity',
        <String, Object?>{'key': key, 'value': value},
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    });
    await batch.commit(noResult: true);
  }

  static String _clamp(String value, int max) {
    final trimmed = value.trim();
    return clampUtf8(trimmed, max);
  }

  static String generateVesselId() {
    final random = Random.secure();
    final buffer = StringBuffer();
    for (var i = 0; i < AqOneConfig.maxVesselIdLength; i++) {
      buffer.write(random.nextInt(16).toRadixString(16));
    }
    return buffer.toString();
  }
}

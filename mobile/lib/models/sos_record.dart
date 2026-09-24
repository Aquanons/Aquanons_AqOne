import '../core/config.dart';
import 'delivery_state.dart';
import 'trust_tier.dart';

const Object _unset = Object();

class SosRecord {
  const SosRecord({
    required this.localId,
    required this.vesselId,
    required this.boat,
    required this.clientTs,
    required this.state,
    this.trustTier = TrustTier.selfDeclared,
    this.lat,
    this.lon,
    this.note,
    this.buoyId,
    this.srcId,
    this.seq,
    this.serverTs,
    this.attempts = 0,
    this.lastError,
    this.relayedAt,
    this.deliveredAt,
    this.acknowledgedAt,
    this.ackedBy,
    this.remoteId,
    this.etaAt,
    this.responderStatus,
    this.responderNote,
    this.fisherReply,
    this.fisherReplySynced = false,
    this.resolvedAt,
    this.lastAttemptAt,
    this.nonce,
  });

  final String localId;
  final String vesselId;
  final String boat;
  final int clientTs;
  final DeliveryState state;
  final int? lastAttemptAt;
  final int? nonce;

  /// How corroborated the sending vessel was when this SOS was raised.
  ///
  /// Snapshotted onto the record rather than read live, so the dispatcher
  /// sees what was true at the time of the call. This is triage context, not
  /// a filter - the app relays every SOS regardless of tier.
  final TrustTier trustTier;
  final double? lat;
  final double? lon;
  final String? note;

  /// The firmware's `BUOY_ID` string (e.g. `"BUOY01"`), not a numeric id -
  /// see docs/21_WEEK1_CONTRACT_FIXTURES.md and BuoyAck.buoyId.
  final String? buoyId;
  final int? srcId;
  final int? seq;
  final int? serverTs;
  final int attempts;
  final String? lastError;
  final int? relayedAt;
  final int? deliveredAt;
  final int? acknowledgedAt;
  final String? ackedBy;

  /// The backend's id for this incident, learned when the responder answers.
  /// Needed to post the fisher's reply against the right event.
  final String? remoteId;

  /// Absolute arrival time as an ISO string, not a duration. A duration decays
  /// in transit; a timestamp stays correct however slow delivery was.
  final String? etaAt;

  /// 1 RECEIVED, 2 DISPATCHED, 3 COAST_GUARD, 4 NEAREST_VESSEL, 5 DELAYED.
  final int? responderStatus;
  final String? responderNote;

  /// 1 STILL_IN_DANGER, 2 SAFE_NOW.
  final int? fisherReply;

  /// Whether the fisher's reply has been successfully confirmed by the backend.
  final bool fisherReplySynced;

  /// When the MDRRMO closed this incident out (ISO string). Null until a
  /// responder resolves it on the dashboard; reconcile() saves it once the
  /// backend read-back reports it.
  final String? resolvedAt;

  /// Parsed ETA, or null when none has arrived.
  DateTime? get etaTime => etaAt == null ? null : DateTime.tryParse(etaAt!)?.toLocal();

  /// Parsed resolution time, or null while the incident is still open.
  DateTime? get resolvedTime =>
      resolvedAt == null ? null : DateTime.tryParse(resolvedAt!)?.toLocal();

  /// True once the promised arrival time has passed with no resolution.
  ///
  /// The UI must switch to "delayed - still en route" here rather than showing
  /// 00:00. A countdown that expires into silence reads as "the rescue failed",
  /// which is both untrue and dangerous for someone deciding whether to swim.
  bool get etaOverdue {
    final eta = etaTime;
    return eta != null && DateTime.now().isAfter(eta);
  }

  bool get hasFix => lat != null && lon != null;

  /// The fisher stood this SOS down themselves (reply 2 = "safe now"),
  /// raised either through the responder-acknowledgement flow or the
  /// post-dispatch "slide to stand down" control. The dashboard treats both
  /// the same way - resolved, off the active queue - once the backend has it.
  bool get isStoodDown => fisherReply == 2 && fisherReplySynced;

  /// The MDRRMO resolved this incident on the dashboard, or the fisher stood
  /// it down themselves. Either way rescue is over and the ETA no longer
  /// counts down.
  bool get isResolved => resolvedAt != null || isStoodDown;

  bool get awaitsRelay => state == DeliveryState.saved;

  bool get awaitsReconcile =>
      state == DeliveryState.relayed || state == DeliveryState.delivered;

  DateTime get createdAt =>
      DateTime.fromMillisecondsSinceEpoch(clientTs * 1000, isUtc: true).toLocal();

  SosRecord copyWith({
    DeliveryState? state,
    String? buoyId,
    int? srcId,
    int? seq,
    int? serverTs,
    int? attempts,
    Object? lastError = _unset,
    int? relayedAt,
    int? deliveredAt,
    int? acknowledgedAt,
    String? ackedBy,
    String? remoteId,
    int? lastAttemptAt,
    int? nonce,
  }) {
    return SosRecord(
      localId: localId,
      vesselId: vesselId,
      boat: boat,
      clientTs: clientTs,
      state: state ?? this.state,
      trustTier: trustTier,
      lat: lat,
      lon: lon,
      note: note,
      buoyId: buoyId ?? this.buoyId,
      srcId: srcId ?? this.srcId,
      seq: seq ?? this.seq,
      serverTs: serverTs ?? this.serverTs,
      attempts: attempts ?? this.attempts,
      lastError: identical(lastError, _unset)
          ? this.lastError
          : lastError as String?,
      relayedAt: relayedAt ?? this.relayedAt,
      deliveredAt: deliveredAt ?? this.deliveredAt,
      acknowledgedAt: acknowledgedAt ?? this.acknowledgedAt,
      ackedBy: ackedBy ?? this.ackedBy,
      remoteId: remoteId ?? this.remoteId,
      lastAttemptAt: lastAttemptAt ?? this.lastAttemptAt,
      nonce: nonce ?? this.nonce,
      // Carried through unchanged. copyWith feeds save(), and dropping these
      // would blank a live ETA in memory every time the delivery state moved.
      // toRow() deliberately does not write them, so saveResponder stays the
      // single writer of responder data.
      etaAt: etaAt,
      responderStatus: responderStatus,
      responderNote: responderNote,
      fisherReply: fisherReply,
      fisherReplySynced: fisherReplySynced,
      resolvedAt: resolvedAt,
    );
  }

  Map<String, Object?> toRow() => <String, Object?>{
        'local_id': localId,
        'vessel_id': vesselId,
        'boat': boat,
        'client_ts': clientTs,
        'state': state.wire,
        'trust_tier': trustTier.wire,
        'lat': lat,
        'lon': lon,
        'note': note,
        'buoy_id': buoyId,
        'src_id': srcId,
        'seq': seq,
        'server_ts': serverTs,
        'attempts': attempts,
        'last_error': lastError,
        'relayed_at': relayedAt,
        'delivered_at': deliveredAt,
        'acknowledged_at': acknowledgedAt,
        'acked_by': ackedBy,
        'last_attempt_at': lastAttemptAt,
        'nonce': nonce,
      };

  static SosRecord fromRow(Map<String, Object?> row) => SosRecord(
        localId: row['local_id'] as String,
        vesselId: row['vessel_id'] as String,
        boat: row['boat'] as String,
        clientTs: row['client_ts'] as int,
        state: DeliveryState.fromWire(row['state'] as String?),
        trustTier: TrustTier.fromWire(row['trust_tier'] as String?),
        lat: (row['lat'] as num?)?.toDouble(),
        lon: (row['lon'] as num?)?.toDouble(),
        note: row['note'] as String?,
        // toString() rather than a hard cast: pre-Phase-1 rows may still
        // carry an INTEGER-affinity value from before buoy_id became a
        // string (see app_database.dart schema note), and this keeps old
        // outbox rows readable instead of crashing on upgrade.
        buoyId: row['buoy_id']?.toString(),
        srcId: (row['src_id'] as num?)?.toInt(),
        seq: (row['seq'] as num?)?.toInt(),
        serverTs: (row['server_ts'] as num?)?.toInt(),
        attempts: (row['attempts'] as num?)?.toInt() ?? 0,
        lastError: row['last_error'] as String?,
        relayedAt: (row['relayed_at'] as num?)?.toInt(),
        deliveredAt: (row['delivered_at'] as num?)?.toInt(),
        acknowledgedAt: (row['acknowledged_at'] as num?)?.toInt(),
        ackedBy: row['acked_by'] as String?,
        remoteId: row['remote_id'] as String?,
        etaAt: row['eta_at'] as String?,
        responderStatus: (row['responder_status'] as num?)?.toInt(),
        responderNote: row['responder_note'] as String?,
        fisherReply: (row['fisher_reply'] as num?)?.toInt(),
        fisherReplySynced:
            ((row['fisher_reply_synced'] as num?)?.toInt() ?? 0) != 0,
        resolvedAt: row['resolved_at'] as String?,
        lastAttemptAt: (row['last_attempt_at'] as num?)?.toInt(),
        nonce: (row['nonce'] as num?)?.toInt(),
      );

  Map<String, Object?> toBuoyPayload() {
    final payload = <String, Object?>{
      'v': AqOneConfig.protocolVersion,
      'vessel_id': vesselId,
      'boat': boat,
      'client_ts': clientTs,
      // Tier only. The name, licence and phone stay off this packet on
      // purpose: they are sent once at registration and looked up by
      // vessel_id, because a LoRa frame has no room to carry them on every
      // distress call.
      'trust_tier': trustTier.wire,
    };
    if (lat != null) {
      payload['lat'] = lat;
    }
    if (lon != null) {
      payload['lon'] = lon;
    }
    final trimmed = note?.trim();
    if (trimmed != null && trimmed.isNotEmpty) {
      payload['note'] = trimmed;
    }
    return payload;
  }
}

import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../core/config.dart';
import '../data/identity_store.dart';
import '../data/outbox_store.dart';
import '../models/buoy_contact.dart';
import '../models/delivery_policy.dart';
import '../models/delivery_state.dart';
import '../models/sos_record.dart';
import '../models/text_clamp.dart';
import '../models/trust_tier.dart';
import 'backend_client.dart';
import 'buoy_client.dart';
import 'location_service.dart';

class SosService {
  SosService({
    required OutboxStore outbox,
    required IdentityStore identity,
    required BuoyClient buoy,
    required BackendClient backend,
    required LocationService location,
    Duration lateFixPollInterval = const Duration(seconds: 5),
    Duration lateFixTimeout = const Duration(minutes: 5),
  })  : _outbox = outbox,
        _identity = identity,
        _buoy = buoy,
        _backend = backend,
        _location = location,
        _lateFixPollInterval = lateFixPollInterval,
        _lateFixTimeout = lateFixTimeout;

  final OutboxStore _outbox;
  final IdentityStore _identity;
  final BuoyClient _buoy;
  final BackendClient _backend;
  final LocationService _location;
  final Duration _lateFixPollInterval;
  final Duration _lateFixTimeout;

  final StreamController<void> _changes = StreamController<void>.broadcast();
  Stream<void> get changes => _changes.stream;

  Timer? _relayTimer;
  Timer? _reconcileTimer;
  bool _relayRunning = false;
  bool _reconcileRunning = false;
  final Set<String> _closedIncidents = <String>{};
  final Map<String, int> _pendingReplies = <String, int>{};

  Duration closureReconcileWindow = const Duration(hours: 2);

  @visibleForTesting
  Set<String> get closedIncidents => _closedIncidents;

  void start() {
    _relayTimer ??= Timer.periodic(
      AqOneConfig.outboxRetryInterval,
      (_) => retryPending(),
    );
    _reconcileTimer ??= Timer.periodic(
      AqOneConfig.reconcileInterval,
      (_) => reconcile(),
    );
  }

  void dispose() {
    _relayTimer?.cancel();
    _reconcileTimer?.cancel();
    _relayTimer = null;
    _reconcileTimer = null;
    _closedIncidents.clear();
    _pendingReplies.clear();
    _changes.close();
  }

  Future<List<SosRecord>> history() => _outbox.all();

  Future<SosRecord> raiseSos({String? note}) async {
    final identity = await _identity.read();
    final vesselId = identity?.vesselId;
    if (vesselId == null || vesselId.isEmpty) {
      throw StateError('Vessel identity is not set up.');
    }

    final nonce = Random.secure().nextInt(1 << 32);
    final fix = await _location.currentFix();
    final record = SosRecord(
      localId: _newLocalId(),
      vesselId: vesselId,
      boat: identity?.boat ?? '',
      clientTs: DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000,
      state: DeliveryState.saved,
      trustTier: identity?.trustTier ?? TrustTier.selfDeclared,
      lat: fix?.lat,
      lon: fix?.lon,
      note: _clampNote(note),
      nonce: nonce,
    );

    await _outbox.insert(record);
    _changes.add(null);

    unawaited(_attemptRelay(record.localId));
    if (fix == null) {
      unawaited(_waitForLateFix(record.localId));
    }
    return record;
  }

  Future<void> _waitForLateFix(String localId) async {
    final deadline = DateTime.now().add(_lateFixTimeout);
    while (DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(_lateFixPollInterval);
      if (_changes.isClosed) {
        return;
      }
      final current = await _outbox.byLocalId(localId);
      if (current == null || current.hasFix) {
        return;
      }
      final fix = await _location.currentFix();
      if (fix != null) {
        final filled = await _outbox.fillPosition(localId, fix.lat, fix.lon);
        if (filled) {
          await _attemptRelay(
            localId,
            routes: {SosRoute.pod, SosRoute.direct},
          );
        }
        return;
      }
    }
  }

  OutboxStore get outbox => _outbox;

  Future<bool> deleteUnsent(String localId) => _outbox.deleteUnsent(localId);

  Future<void> retryPending() async {
    if (_relayRunning) {
      return;
    }
    _relayRunning = true;
    try {
      final now = DateTime.now();
      final pending = await _outbox.awaitingDelivery();
      for (final record in pending) {
        final routes = routesDue(record, now);
        if (routes.isEmpty) {
          continue;
        }
        final ok = await _attemptRelay(
          record.localId,
          routes: routes,
          notify: false,
        );
        if (!ok) {
          break;
        }
      }
    } finally {
      _relayRunning = false;
      _changes.add(null);
    }
  }

  /// Deliver one SOS by every route available, and stop once any succeeds.
  ///
  /// Three layers, in the order they can be relied on:
  ///
  ///   1. local   the record is already in the outbox before this runs, so the
  ///              SOS survives a dead battery, a crash or a reinstall
  ///   2. buoy    phone -> WiFi -> LoRa mesh -> gateway -> backend, the route
  ///              that works with no cellular signal at all
  ///   3. direct  phone -> HTTPS -> backend, when the handset has internet
  ///
  /// Both transports are attempted, not one as a fallback for the other. For a
  /// distress call redundancy beats tidiness: the buoy may be out of range and
  /// the cell signal may be marginal, and there is no way to know in advance
  /// which will get through. The backend de-duplicates on
  /// (vessel_id, client_ts), so two successful deliveries are still one
  /// incident on the dispatcher's screen.
  Future<bool> _attemptRelay(
    String localId, {
    Set<SosRoute>? routes,
    bool notify = true,
  }) async {
    final record = await _outbox.byLocalId(localId);
    if (record == null) {
      return true;
    }
    final activeRoutes = routes ?? routesDue(record, DateTime.now());
    if (activeRoutes.isEmpty) {
      return true;
    }

    // Fired together rather than sequentially - waiting for a 6-second buoy
    // timeout before trying the internet would delay a distress call for no
    // reason. Each attempt captures its own failure so one route going down
    // never cancels the other.
    Future<Object?> tryBuoy() async {
      try {
        return await _buoy.handoff(record);
      } catch (error) {
        return error;
      }
    }

    Future<bool> tryDirect() async {
      try {
        return await _backend.postSos(record);
      } catch (_) {
        return false;
      }
    }

    Object? buoyResult;
    bool directOk = false;

    if (activeRoutes.contains(SosRoute.pod) &&
        activeRoutes.contains(SosRoute.direct)) {
      final buoyFuture = tryBuoy();
      final directFuture = tryDirect();
      buoyResult = await buoyFuture;
      directOk = await directFuture;
    } else if (activeRoutes.contains(SosRoute.pod)) {
      buoyResult = await tryBuoy();
    } else if (activeRoutes.contains(SosRoute.direct)) {
      directOk = await tryDirect();
    }

    await _outbox.recordAttempt(localId, DateTime.now());

    // Both outcomes are processed, not just whichever is checked first - a
    // simultaneous buoy ack and direct success must not leave the record
    // stuck at `relayed` when the backend already has it. Writes stay
    // sequential (not run concurrently with the sends above) so there is no
    // read-modify-write race between them; OutboxStore.advance()'s monotonic
    // merge means the order between them cannot regress the state either way.
    final buoySucceeded = buoyResult is BuoyAck;
    if (buoySucceeded) {
      await _outbox.advance(
        localId,
        DeliveryState.relayed,
        buoyId: buoyResult.buoyId,
        // The firmware's POST /v1/sos response has no src_id field (see
        // docs/21_WEEK1_CONTRACT_FIXTURES.md) - it was never sent, so this is
        // left unpopulated rather than fabricated.
        seq: buoyResult.seq,
        serverTs: buoyResult.serverTs,
      );
    }
    if (directOk) {
      // The backend has it. No buoy metadata passed here - if the buoy also
      // succeeded above, its metadata is already saved and copyWith() keeps
      // it; if not, there is none to record.
      await _outbox.advance(localId, DeliveryState.delivered);
      unawaited(_refreshVesselProfile());
    }

    if (buoySucceeded || directOk) {
      if (notify) {
        _changes.add(null);
      }
      return true;
    }

    final reason = _failureReason(buoyResult);
    await _outbox.recordFailure(localId, reason);
    if (notify) {
      _changes.add(null);
    }
    return false;
  }

  String _failureReason(Object? buoyResult) {
    final directReason = _backend.lastDirectError ?? 'internet path failed';
    if (buoyResult == null) {
      return directReason;
    }
    final buoyReason = buoyResult is BuoyRejected
        ? buoyResult.reason
        : buoyResult is BuoyUnreachable
            ? 'Not connected to the buoy'
            : buoyResult is BuoyInvalidResponse
                ? buoyResult.reason
                : 'no buoy in range';
    return '$buoyReason · $directReason';
  }

  Future<void> _refreshVesselProfile() async {
    try {
      final identity = await _identity.read();
      if (identity != null && identity.isComplete) {
        await _backend.registerVesselProfile(identity);
      }
    } catch (_) {}
  }

  /// Send the fisher's one-tap answer to a responder acknowledgement.
  ///
  /// 1 = still in danger, 2 = safe now. Saved locally first so the button
  /// reflects what the fisher pressed even if the network call fails - being
  /// told "your reply failed" while waiting for rescue is worse than useless,
  /// and the record is retried by the normal reconcile cycle.
  Future<bool> replyToSos(String localId, int reply) async {
    final record = await _outbox.byLocalId(localId);
    if (record == null) {
      return false;
    }
    await _outbox.saveFisherReply(localId, reply, synced: false);
    _changes.add(null);

    final remoteId = record.remoteId;
    if (remoteId == null) {
      // The backend has not told us its id for this incident yet, so there is
      // nothing to attach the reply to. The next reconcile will bring it.
      _pendingReplies[localId] = reply;
      return false;
    }
    final ok = await _sendReply(record, reply);
    if (!ok) {
      _pendingReplies[localId] = reply;
    }
    return ok;
  }

  Future<bool> _sendReply(SosRecord record, int reply) async {
    final remoteId = record.remoteId;
    if (remoteId == null) {
      return false;
    }
    // SEC-21: Before an un-credentialed handset replies to a record the
    // backend has not confirmed as delivered over the direct path, re-post
    // the same SOS directly. This is idempotent on (vessel_id, client_ts) and
    // records the local_id on the backend so the reply route matches.
    if (!_backend.hasVesselCredential) {
      try {
        await _backend.postSos(record);
      } catch (_) {}
    }
    final ok = await _backend.replyToSos(
      int.tryParse(remoteId) ?? -1,
      reply,
      localId: record.localId,
    );
    if (ok) {
      await _outbox.markFisherReplySynced(record.localId);
      _pendingReplies.remove(record.localId);
      _changes.add(null);
    }
    return ok;
  }

  /// Attaches (or fills in) the note on an SOS already dispatched.
  ///
  /// The initial `raiseSos()` call is deliberately sent with no note, so
  /// choosing an emergency type never delays the alert itself. This is what
  /// the fisher's "what's wrong?" follow-up calls once they pick one.
  ///
  /// Best-effort: the note is saved locally immediately (so the app's own
  /// history always shows it), and a single attempt is made to push it to
  /// the backend right away over whichever transport is reachable. The
  /// backend's ingest is idempotent on (vessel_id, client_ts) and only fills
  /// a note that is still empty, so re-posting the same SOS is always safe -
  /// it can never overwrite a note that was already recorded. If neither
  /// transport is reachable at that moment, the note stays local-only for
  /// this version rather than being retried indefinitely in the background.
  Future<SosRecord> amendNote(String localId, String note) async {
    await _outbox.updateNote(localId, note);
    final updated = await _outbox.byLocalId(localId);
    _changes.add(null);
    if (updated == null) {
      throw StateError('amendNote called for an SOS that no longer exists');
    }

    unawaited(() async {
      try {
        await _buoy.handoff(updated);
      } catch (_) {}
      try {
        await _backend.postSos(updated);
      } catch (_) {}
    }());

    return updated;
  }

  /// The fisher standing down their own SOS - "false alarm, disregard" -
  /// from the post-dispatch follow-up screen rather than waiting for a
  /// responder to acknowledge first.
  ///
  /// Reuses the same reply=2 ("safe now") signal the acknowledgement flow
  /// sends, since that is the only thing on the backend that resolves an
  /// incident and takes it off the MDRRMO's active queue - there is no
  /// separate cancel endpoint. The reply requires a backend event id, which
  /// an SOS only gets once it has actually reached the backend. If that
  /// has not happened yet, the stand-down is saved locally and
  /// [_applyRemote] sends it the moment reconcile learns the event id -
  /// see the fisherReply check there.
  Future<void> standDown(String localId) async {
    final record = await _outbox.byLocalId(localId);
    if (record == null) {
      return;
    }
    await _outbox.saveFisherReply(localId, 2, synced: false);
    _changes.add(null);

    final remoteId = record.remoteId;
    if (remoteId == null) {
      // Nothing more to do now - reconcile() will flush this once the
      // event id arrives.
      _pendingReplies[localId] = 2;
      return;
    }
    final ok = await _sendReply(record, 2);
    if (!ok) {
      _pendingReplies[localId] = 2;
    }
  }

  Future<BuoyStatus?> pollBuoy() async {
    try {
      return await _buoy.status();
    } catch (_) {
      return null;
    }
  }

  /// Reconciles pending SOS records against whichever source can currently
  /// answer for them.
  ///
  /// The direct internet path is preferred when it is up - it is the
  /// backend's own data, not a relay of it. But a handset with no cellular
  /// signal is exactly the case this whole app exists for, and it is
  /// precisely when the backend's `/healthz` check will fail. Previously
  /// reconcile() simply gave up at that point: an offline fisher who had
  /// already been acknowledged and given an ETA would never find out, even
  /// though the buoy in range of the phone had that answer cached
  /// (`GET /v1/sos/status`, which the firmware fills in by polling the
  /// backend on the handset's behalf - docs/21_WEEK1_CONTRACT_FIXTURES.md).
  Future<void> reconcile() async {
    if (_reconcileRunning) {
      return;
    }
    _reconcileRunning = true;
    try {
      final allAwaiting = await _outbox.awaitingReconcile();
      final now = DateTime.now().toUtc();
      for (final r in allAwaiting) {
        final res = r.resolvedTime;
        if (res != null && now.difference(res) >= closureReconcileWindow) {
          _closedIncidents.add(r.localId);
        } else if (res != null) {
          _closedIncidents.remove(r.localId);
        }
      }
      final pending = allAwaiting
          .where((r) => !_closedIncidents.contains(r.localId))
          .toList(growable: false);
      if (pending.isEmpty) {
        return;
      }

      final vesselIds = pending.map((record) => record.vesselId).toSet();
      var changed = false;
      final backendUp = await _backend.isReachable();
      final cloudUp = backendUp && _backend.hasVesselCredential;

      for (final vesselId in vesselIds) {
        final records = pending.where((r) => r.vesselId == vesselId).toList();
        List<RemoteSos> remote;
        if (cloudUp) {
          remote = await _backend.vesselSos(vesselId);
        } else if (backendUp) {
          // No vessel credential (and possibly no enrolment UI to ever get
          // one), but the backend is reachable over the same internet that
          // carried the SOS. The direct path asked without a credential, so
          // it reads the answer the same way - one ack per record, by the
          // local_id only this phone knows (GET /api/sos/ack/{local_id}).
          remote = <RemoteSos>[];
          for (final record in records) {
            final ack = await _backend.ackByLocalId(record.localId);
            if (ack != null) {
              remote.add(ack);
            }
          }
          // A record that reached the backend only over the buoy has no
          // local_id there for ackByLocalId() to answer with, so let the
          // buoy - which proxies the credentialed feed - speak for the
          // records the backend did not match. Unreachable buoy is not an
          // error here: whatever ackByLocalId() already found still applies.
          if (remote.length < records.length) {
            try {
              remote = <RemoteSos>[...remote, ...await _buoy.sosStatus(vesselId)];
            } catch (_) {}
          }
        } else {
          try {
            remote = await _buoy.sosStatus(vesselId);
          } catch (_) {
            // Buoy unreachable, rejected the query, or sent an unreadable
            // body. Skip this vessel this tick - the record stays exactly as
            // it was (no regression) and the next reconcile tick tries
            // again. One bad vessel/buoy must not stop the others in
            // [vesselIds] from being checked.
            continue;
          }
        }
        if (await _applyRemote(records, remote)) {
          changed = true;
        }
      }

      if (changed) {
        _changes.add(null);
      }
    } catch (_) {
      return;
    } finally {
      _reconcileRunning = false;
    }
  }

  /// Matches this vessel's pending outbox records against a set of remote
  /// events (from either the backend directly or the buoy's cached proxy of
  /// it) and applies whatever is new. Returns true if anything changed.
  Future<bool> _applyRemote(
    List<SosRecord> records,
    List<RemoteSos> remote,
  ) async {
    if (remote.isEmpty) {
      return false;
    }
    var changed = false;

    final claimedEvents = <RemoteSos>{};
    final matches = <SosRecord, RemoteSos>{};

    void claim(bool Function(SosRecord, RemoteSos) matchesBy) {
      for (final record in records) {
        if (matches.containsKey(record)) continue;
        for (final event in remote) {
          if (!claimedEvents.contains(event) && matchesBy(record, event)) {
            matches[record] = event;
            claimedEvents.add(event);
            break;
          }
        }
      }
    }

    claim((record, event) =>
        event.localId != null && event.localId!.isNotEmpty && event.localId == record.localId);
    claim((record, event) => record.nonce != null && event.nonce == record.nonce);
    claim((record, event) =>
        record.seq != null &&
        event.seq == record.seq &&
        (event.nonce == null || record.nonce == null || event.nonce == record.nonce));

    for (final entry in matches.entries) {
      final record = entry.key;
      final match = entry.value;
      // _outbox.advance() merges state forward only (DeliveryState.merge),
      // so a stale or partial answer from either source can never regress an
      // already-confirmed state - see docs/06_DELIVERY_STATES.md.
      final advanced = await _outbox.advance(
        record.localId,
        match.deliveryState,
        ackedBy: match.ackedBy,
      );
      if (advanced != null && advanced.state != record.state) {
        changed = true;
      }
      // SEC-22: Store the ETA converted to the device clock:
      // device now plus (eta_at minus server_time). Without server_time, keep
      // today's behaviour. If an ETA has already been stored and differs from
      // the converted time by less than 30 seconds, keep the stored value so
      // ticks with the same answer write nothing and emit no change.
      String? adjustedEtaAt = match.etaAt;
      if (match.etaAt != null && match.serverTime != null) {
        final serverEta = DateTime.tryParse(match.etaAt!);
        final serverNow = DateTime.tryParse(match.serverTime!);
        if (serverEta != null && serverNow != null) {
          final remaining = serverEta.difference(serverNow);
          final deviceEta = DateTime.now().toUtc().add(remaining);
          if (record.etaAt != null) {
            final storedEta = DateTime.tryParse(record.etaAt!);
            if (storedEta != null &&
                (deviceEta.difference(storedEta).inMilliseconds.abs() < 30000)) {
              adjustedEtaAt = record.etaAt;
            } else {
              adjustedEtaAt = deviceEta.toIso8601String();
            }
          } else {
            adjustedEtaAt = deviceEta.toIso8601String();
          }
        }
      }

      // Reopen handling: when remote row has reopened_at later than local resolvedAt,
      // clear it with OutboxStore.clearResolved(localId), which also resets the stand-down.
      final localResolved = record.resolvedTime;
      final remoteReopened = match.reopenedAt != null
          ? DateTime.tryParse(match.reopenedAt!)?.toUtc()
          : null;
      final remoteResolved = match.resolvedAt != null
          ? DateTime.tryParse(match.resolvedAt!)?.toUtc()
          : null;

      final isReopened = remoteReopened != null &&
          localResolved != null &&
          remoteReopened.isAfter(localResolved) &&
          (remoteResolved == null || remoteReopened.isAfter(remoteResolved));

      if (isReopened) {
        await _outbox.clearResolved(record.localId);
        _closedIncidents.remove(record.localId);
        changed = true;
      }

      final resolvedAtToSave = isReopened ? null : match.resolvedAt;
      final shouldMarkSynced = resolvedAtToSave != null ||
          (record.fisherReply != null && match.fisherReply == record.fisherReply);

      // Responder details live alongside the delivery state: the ETA and
      // status are what the fisher is actually waiting to see.
      final stored = await _outbox.saveResponder(
        record.localId,
        remoteId: match.id,
        etaAt: adjustedEtaAt,
        responderStatus: match.responderStatus,
        responderNote: match.responderNote ?? match.responderStatusLabel,
        resolvedAt: resolvedAtToSave,
        fisherReplySynced: shouldMarkSynced ? true : null,
      );
      if (stored) {
        changed = true;
      }

      // Any fisher reply saved locally before the backend had assigned this SOS
      // an event id - or while the vessel credential was absent/revoked, or if a
      // previous attempt failed - can be flushed once reconcile knows the backend id.
      final isReplySynced = shouldMarkSynced || record.fisherReplySynced;
      final pendingReply = _pendingReplies[record.localId] ??
          (!isReplySynced ? record.fisherReply : null);
      if (pendingReply != null && match.id.isNotEmpty) {
        try {
          final ok = await _sendReply(
            record.copyWith(remoteId: match.id),
            pendingReply,
          );
          if (ok) {
            changed = true;
          }
        } catch (_) {}
      }

      if (resolvedAtToSave != null && !_pendingReplies.containsKey(record.localId)) {
        final resTime = remoteResolved ?? DateTime.now().toUtc();
        if (DateTime.now().toUtc().difference(resTime) >= closureReconcileWindow) {
          _closedIncidents.add(record.localId);
        } else {
          _closedIncidents.remove(record.localId);
        }
      }

    }
    return changed;
  }

  static String? _clampNote(String? note) {
    final trimmed = note?.trim();
    if (trimmed == null || trimmed.isEmpty) {
      return null;
    }
    return clampUtf8(trimmed, AqOneConfig.maxNoteBytes);
  }

  static String _newLocalId() {
    final random = Random.secure();
    final stamp = DateTime.now().toUtc().millisecondsSinceEpoch;
    final suffix = List<String>.generate(
      8,
      (_) => random.nextInt(16).toRadixString(16),
    ).join();
    return '$stamp-$suffix';
  }
}

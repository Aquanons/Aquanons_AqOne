import 'package:sqflite/sqflite.dart';

import '../models/delivery_state.dart';
import '../models/sos_record.dart';
import 'app_database.dart';

class OutboxStore {
  OutboxStore(this._db);

  final AppDatabase _db;

  Future<void> insert(SosRecord record) async {
    final db = await _db.database;
    await db.insert(
      'outbox',
      record.toRow(),
      conflictAlgorithm: ConflictAlgorithm.abort,
    );
  }

  Future<List<SosRecord>> all({int limit = 100}) async {
    final db = await _db.database;
    final rows = await db.query(
      'outbox',
      orderBy: 'client_ts DESC',
      limit: limit,
    );
    return rows.map(SosRecord.fromRow).toList(growable: false);
  }

  Future<SosRecord?> byLocalId(String localId) async {
    final db = await _db.database;
    final rows = await db.query(
      'outbox',
      where: 'local_id = ?',
      whereArgs: <Object?>[localId],
      limit: 1,
    );
    return rows.isEmpty ? null : SosRecord.fromRow(rows.first);
  }

  Future<List<SosRecord>> awaitingDelivery() async {
    final db = await _db.database;
    final rows = await db.query(
      'outbox',
      where: 'state IN (?, ?)',
      whereArgs: <Object?>[
        DeliveryState.saved.wire,
        DeliveryState.relayed.wire,
      ],
      orderBy: 'client_ts ASC',
    );
    return rows.map(SosRecord.fromRow).toList(growable: false);
  }

  Future<List<SosRecord>> awaitingReconcile({Set<String>? excludedIds}) async {
    final db = await _db.database;
    final rows = await db.query(
      'outbox',
      where: 'state IN (?, ?, ?)',
      whereArgs: <Object?>[
        DeliveryState.relayed.wire,
        DeliveryState.delivered.wire,
        DeliveryState.acknowledged.wire,
      ],
      orderBy: 'client_ts ASC',
    );
    final records = rows.map(SosRecord.fromRow).toList(growable: false);
    if (excludedIds != null && excludedIds.isNotEmpty) {
      return records
          .where((r) => !excludedIds.contains(r.localId))
          .toList(growable: false);
    }
    return records;
  }

  Future<SosRecord> save(SosRecord record) async {
    final db = await _db.database;
    return await db.transaction((txn) async {
      final rows = await txn.query(
        'outbox',
        where: 'local_id = ?',
        whereArgs: <Object?>[record.localId],
      );
      if (rows.isEmpty) {
        await txn.insert('outbox', record.toRow());
        return record;
      }
      final existing = SosRecord.fromRow(rows.first);
      final mergedState = existing.state.merge(record.state);
      final merged = record.copyWith(
        state: mergedState,
        buoyId: record.buoyId ?? existing.buoyId,
        srcId: record.srcId ?? existing.srcId,
        seq: record.seq ?? existing.seq,
        serverTs: record.serverTs ?? existing.serverTs,
        relayedAt: existing.relayedAt ?? record.relayedAt,
        deliveredAt: existing.deliveredAt ?? record.deliveredAt,
        acknowledgedAt: existing.acknowledgedAt ?? record.acknowledgedAt,
        ackedBy: record.ackedBy ?? existing.ackedBy,
        lastError: record.state.rank > existing.state.rank
            ? record.lastError
            : (record.lastError ?? existing.lastError),
      );
      final row = merged.toRow();
      if (record.note == null && existing.note != null) {
        row['note'] = existing.note;
      }
      await txn.update(
        'outbox',
        row,
        where: 'local_id = ?',
        whereArgs: <Object?>[record.localId],
      );
      return merged;
    });
  }

  Future<SosRecord?> advance(
    String localId,
    DeliveryState candidate, {
    String? buoyId,
    int? srcId,
    int? seq,
    int? serverTs,
    String? ackedBy,
  }) async {
    final current = await byLocalId(localId);
    if (current == null) {
      return null;
    }

    final next = current.state.merge(candidate);
    if (next == current.state &&
        buoyId == null &&
        srcId == null &&
        seq == null &&
        ackedBy == null) {
      return current;
    }

    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    final updated = current.copyWith(
      state: next,
      buoyId: buoyId,
      srcId: srcId,
      seq: seq,
      serverTs: serverTs,
      ackedBy: ackedBy,
      lastError: null,
      relayedAt: next.rank >= DeliveryState.relayed.rank
          ? (current.relayedAt ?? now)
          : current.relayedAt,
      deliveredAt: next.rank >= DeliveryState.delivered.rank
          ? (current.deliveredAt ?? now)
          : current.deliveredAt,
      acknowledgedAt: next.rank >= DeliveryState.acknowledged.rank
          ? (current.acknowledgedAt ?? now)
          : current.acknowledgedAt,
    );
    return save(updated);
  }

  /// Store what the responder sent back for this SOS.
  ///
  /// Returns true when something actually changed, so the caller only pushes a
  /// UI update when there is news - a poll every 15 seconds that reports "no
  /// change" should not repaint a countdown the user is watching.
  Future<bool> saveResponder(
    String localId, {
    String? remoteId,
    String? etaAt,
    int? responderStatus,
    String? responderNote,
    String? resolvedAt,
    bool? fisherReplySynced,
  }) async {
    final db = await _db.database;
    final existing = await db.query(
      'outbox',
      columns: <String>[
        'remote_id',
        'eta_at',
        'responder_status',
        'responder_note',
        'resolved_at',
        'fisher_reply_synced',
      ],
      where: 'local_id = ?',
      whereArgs: <Object?>[localId],
      limit: 1,
    );
    if (existing.isEmpty) {
      return false;
    }
    final row = existing.first;

    final shouldMarkSynced = (resolvedAt != null || fisherReplySynced == true);
    final next = <String, Object?>{
      if (remoteId != null && row['remote_id'] != remoteId) 'remote_id': remoteId,
      if (etaAt != null && row['eta_at'] != etaAt) 'eta_at': etaAt,
      if (responderStatus != null && row['responder_status'] != responderStatus)
        'responder_status': responderStatus,
      if (responderNote != null && row['responder_note'] != responderNote)
        'responder_note': responderNote,
      if (resolvedAt != null && row['resolved_at'] != resolvedAt)
        'resolved_at': resolvedAt,
      if (shouldMarkSynced && ((row['fisher_reply_synced'] as num?)?.toInt() ?? 0) != 1)
        'fisher_reply_synced': 1,
    };
    if (next.isEmpty) {
      return false;
    }

    await db.update(
      'outbox',
      next,
      where: 'local_id = ?',
      whereArgs: <Object?>[localId],
    );
    return true;
  }

  /// Clears resolution and stand-down when an incident is reopened.
  Future<void> clearResolved(String localId) async {
    final db = await _db.database;
    await db.update(
      'outbox',
      <String, Object?>{
        'resolved_at': null,
        'fisher_reply': null,
        'fisher_reply_synced': 0,
      },
      where: 'local_id = ?',
      whereArgs: <Object?>[localId],
    );
  }

  /// Updates the note on an SOS already in the outbox.
  ///
  /// Used by the post-dispatch "what's wrong?" follow-up: the initial send
  /// goes out with no note so it is never delayed waiting on the fisher to
  /// type, and the chosen emergency type/description is attached afterwards.
  Future<void> updateNote(String localId, String note) async {
    final db = await _db.database;
    await db.update(
      'outbox',
      <String, Object?>{'note': note},
      where: 'local_id = ?',
      whereArgs: <Object?>[localId],
    );
  }

  /// Fills GPS position on an outbox record that was dispatched without a fix.
  /// Only updates if lat/lon are still null.
  Future<bool> fillPosition(String localId, double lat, double lon) async {
    final db = await _db.database;
    final count = await db.update(
      'outbox',
      <String, Object?>{
        'lat': lat,
        'lon': lon,
      },
      where: 'local_id = ? AND lat IS NULL AND lon IS NULL',
      whereArgs: <Object?>[localId],
    );
    return count > 0;
  }

  /// Record the fisher's own reply locally, so the button reflects reality even
  /// if the network call to the backend fails.
  Future<void> saveFisherReply(
    String localId,
    int reply, {
    bool synced = false,
  }) async {
    final db = await _db.database;
    await db.update(
      'outbox',
      <String, Object?>{
        'fisher_reply': reply,
        'fisher_reply_synced': synced ? 1 : 0,
      },
      where: 'local_id = ?',
      whereArgs: <Object?>[localId],
    );
  }

  /// Mark the fisher's reply as confirmed delivered by the backend.
  Future<void> markFisherReplySynced(String localId) async {
    final db = await _db.database;
    await db.update(
      'outbox',
      <String, Object?>{'fisher_reply_synced': 1},
      where: 'local_id = ?',
      whereArgs: <Object?>[localId],
    );
  }

  Future<void> recordAttempt(String localId, DateTime now) async {
    final db = await _db.database;
    final nowSec = now.toUtc().millisecondsSinceEpoch ~/ 1000;
    await db.rawUpdate(
      'UPDATE outbox SET attempts = attempts + 1, last_attempt_at = ? WHERE local_id = ?',
      <Object?>[nowSec, localId],
    );
  }

  Future<bool> deleteUnsent(String localId) async {
    final db = await _db.database;
    final count = await db.delete(
      'outbox',
      where: 'local_id = ? AND state = ?',
      whereArgs: <Object?>[localId, DeliveryState.saved.wire],
    );
    return count > 0;
  }

  Future<SosRecord?> recordFailure(String localId, String error) async {
    final current = await byLocalId(localId);
    if (current == null) {
      return null;
    }
    return save(
      current.copyWith(attempts: current.attempts + 1, lastError: error),
    );
  }
}

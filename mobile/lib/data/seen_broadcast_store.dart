import 'package:sqflite/sqflite.dart';

import 'app_database.dart';

/// Persists which nearby SOS broadcasts have already rung this phone.
///
/// docs/73 Rev 2 G2: a nearby broadcast rings once per phone, not once per
/// app run.
class SeenBroadcastStore {
  SeenBroadcastStore(this._db);

  final AppDatabase _db;

  /// Returns true only the first time this phone ever sees [broadcastId].
  Future<bool> markSeen(int broadcastId) async {
    final db = await _db.database;
    final existing = await db.query(
      'seen_broadcasts',
      columns: const <String>['broadcast_id'],
      where: 'broadcast_id = ?',
      whereArgs: <Object?>[broadcastId],
      limit: 1,
    );
    if (existing.isNotEmpty) {
      return false;
    }
    try {
      final inserted = await db.insert(
        'seen_broadcasts',
        <String, Object?>{
          'broadcast_id': broadcastId,
          'seen_at': DateTime.now().millisecondsSinceEpoch,
        },
        conflictAlgorithm: ConflictAlgorithm.abort,
      );
      return inserted > 0;
    } catch (_) {
      return false;
    }
  }
}

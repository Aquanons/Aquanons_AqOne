import 'package:sqflite/sqflite.dart';

import 'db_factory.dart';

class AppDatabase {
  AppDatabase({String? overridePath}) : _overridePath = overridePath;

  final String? _overridePath;
  Database? _database;

  Future<Database> get database async {
    final existing = _database;
    if (existing != null) {
      return existing;
    }
    final opened = await _open();
    _database = opened;
    return opened;
  }

  Future<Database> _open() async {
    initDatabaseFactory();
    final path = _overridePath ?? await defaultDatabasePath('aqone_outbox.db');
    return openDatabase(
      path,
      version: 14,
      onConfigure: (db) => db.execute('PRAGMA foreign_keys = ON'),
      onUpgrade: (db, oldVersion, newVersion) async {
        // Each step is wrapped in try/catch so a partially-applied migration
        // (e.g. column already added on a previous crash) doesn't kill the
        // entire openDatabase call.
        if (oldVersion < 2) {
          try {
            await db.execute(
              'ALTER TABLE outbox ADD COLUMN trust_tier TEXT NOT NULL '
              "DEFAULT 'self_declared'",
            );
          } catch (_) {}
        }
        if (oldVersion < 3) {
          // v3 once created the legacy catch_outbox table. Catch logging was
          // removed from the product; nothing runs for this step anymore.
        }
        if (oldVersion < 4) {
          // v4 once dropped catch_outbox. Catch logging was removed from the
          // product; a handset still holding rows simply keeps them, unused.
        }
        if (oldVersion < 5) {
          // v5 stores what the responder sent back, so the ETA survives the
          // app being closed and reopened - which is exactly when a frightened
          // person will check it.
          await _addResponderColumns(db);
        }
        if (oldVersion < 6) {
          // v6: buoy_id is the firmware's BUOY_ID string (e.g. "BUOY01"), not
          // a numeric id - see docs/21_WEEK1_CONTRACT_FIXTURES.md. No column
          // migration is needed: SQLite's INTEGER-affinity storage already
          // accepts and round-trips TEXT values for a column that was never
          // declared STRICT, and SosRecord.fromRow() reads whatever is there
          // with toString(). This upgrade step exists only to document the
          // version bump and the reasoning, so a future migration does not
          // assume buoy_id is still numeric.
        }
        if (oldVersion < 7) {
          // v7 once re-created catch_outbox for catch logging, a feature that
          // has since been removed from the product. No work is done here.
        }
        if (oldVersion < 8) {
          // v8 once recreated catch_outbox to split catch weight into an
          // estimate and a confirmed figure. Catch logging has since been
          // removed from the product. No work is done here.
        }
        if (oldVersion < 9) {
          // v9: the trip checklist moves from in-memory state (reset on
          // every app launch) to a real table, so gear items survive
          // restarts. Persisted locally only - this is a personal packing
          // list, never sent to the backend.
          await _createChecklistItems(db);
        }
        if (oldVersion < 10) {
          // v10 once created fishing_spot_outbox. The dormant exact-spot
          // pipeline was removed; existing tables/rows are preserved untouched.
        }
        if (oldVersion < 11) {
          // v11: offline map. The Venture map's feeds lived in memory only,
          // so closing the app at the dock and reopening it offshore left a
          // blank sea - no buoys, no coverage, no last hazard picture. This
          // holds the last good response per feed so the map is usable with
          // no signal at all.
          await _createMapSnapshot(db);
        }
if (oldVersion < 12) {
          // v12 once added share_for_hotspots to catch_outbox. Catch logging
          // has since been removed from the product. No work is done here.
        }
        if (oldVersion < 13) {
          try {
            await db.execute('ALTER TABLE outbox ADD COLUMN resolved_at TEXT');
          } catch (_) {}
        }
        if (oldVersion < 14) {
          try {
            await db.execute(
              'ALTER TABLE outbox ADD COLUMN fisher_reply_synced INTEGER NOT NULL DEFAULT 0',
            );
          } catch (_) {}
        }
      },
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE identity (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE outbox (
            local_id        TEXT PRIMARY KEY,
            vessel_id       TEXT NOT NULL,
            boat            TEXT NOT NULL,
            client_ts       INTEGER NOT NULL,
            state           TEXT NOT NULL,
            trust_tier      TEXT NOT NULL DEFAULT 'self_declared',
            lat             REAL,
            lon             REAL,
            note            TEXT,
            -- The firmware's BUOY_ID string (e.g. "BUOY01"), not numeric -
            -- see docs/21_WEEK1_CONTRACT_FIXTURES.md.
            buoy_id         TEXT,
            src_id          INTEGER,
            seq             INTEGER,
            server_ts       INTEGER,
            attempts        INTEGER NOT NULL DEFAULT 0,
            last_error      TEXT,
            relayed_at      INTEGER,
            delivered_at    INTEGER,
            acknowledged_at INTEGER,
            acked_by        TEXT,
            -- What the responder sent back. remote_id is the backend's event
            -- id, needed to post the fisher's reply against the right incident.
            remote_id        TEXT,
            eta_at           TEXT,
            responder_status INTEGER,
            responder_note   TEXT,
            fisher_reply     INTEGER,
            fisher_reply_synced INTEGER NOT NULL DEFAULT 0,
            -- When the MDRRMO resolved the incident (ISO string). Null until
            -- then; set by reconcile the first time the backend reports it.
            resolved_at      TEXT
          )
        ''');
        await db.execute(
          'CREATE INDEX idx_outbox_state ON outbox (state, client_ts DESC)',
        );
        await db.execute(
          'CREATE INDEX idx_outbox_seq ON outbox (vessel_id, seq)',
        );
        await _createChecklistItems(db);
        await _createMapSnapshot(db);
      },
    );
  }

/// Legacy outbox rows get their own table rather than sharing [outbox].
  ///
  /// They travel a different route - straight to the backend over HTTP when
  /// signal returns, never over LoRa - and carry entirely different columns.
  /// Folding them into the SOS outbox would mean a dozen nullable columns and
  /// a state machine that means two different things depending on the row.
  /// Columns added in v5 for the responder loop.
  ///
  /// Applied one at a time and tolerantly: SQLite has no ADD COLUMN IF NOT
  /// EXISTS, and a handset that has already been through a partial upgrade
  /// must not be left with an unopenable database mid-emergency.
  static Future<void> _addResponderColumns(Database db) async {
    const columns = <String>[
      'remote_id TEXT',
      'eta_at TEXT',
      'responder_status INTEGER',
      'responder_note TEXT',
      'fisher_reply INTEGER',
    ];
    for (final column in columns) {
      try {
        await db.execute('ALTER TABLE outbox ADD COLUMN $column');
      } catch (_) {
        // Already present.
      }
    }
  }

  /// The trip checklist. `is_done` resets to 0 for every row when a
  /// fisherman taps "New trip" - deliberately not row deletion, so the gear
  /// list itself (and any custom items he's added) survives across trips
  /// and only the checkmarks need re-doing. A boat that goes out two or
  /// three times a day needs that reset to be cheap and frequent.
  static Future<void> _createChecklistItems(Database db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS checklist_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT NOT NULL,
        is_done    INTEGER NOT NULL DEFAULT 0,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL
      )
    ''');
  }

  /// One row per feed, holding the raw JSON exactly as the backend sent it.
  ///
  /// Raw rather than parsed columns on purpose: the models already know how
  /// to read that shape, so a snapshot stays readable when a feed gains a
  /// field, and a schema change on the backend cannot silently corrupt what
  /// a fisherman sees offshore.
  static Future<void> _createMapSnapshot(Database db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS map_snapshot (
        feed       TEXT PRIMARY KEY,
        payload    TEXT NOT NULL,
        fetched_at INTEGER NOT NULL
      )
    ''');
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}

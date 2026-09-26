import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:network_info_plus/network_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/config.dart';
import '../core/endpoint_guard.dart';
import '../data/identity_store.dart';
import '../l10n/app_localizations.dart';

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

/// What this handset actually knows about one of ITS OWN outgoing lines.
///
/// [queuedLocally] means the handset has retained the line but has not put it
/// on the hub's WebSocket yet. [handedToHub] means this handset wrote the
/// line to its active connection to the hub - the current protocol has no
/// hub receipt, so this does not prove the hub stored it, another boat saw
/// it, or it reached shore. Neither state says anything about the cloud
/// relay, which is tracked separately on [ChatMessage.cloudStored] because
/// the two legs succeed or fail independently.
enum ChatHubState { queuedLocally, handedToHub }

class ChatMessage {
  ChatMessage({
    required this.text,
    required this.from,
    required this.isMine,
    required this.time,
    this.hubState = ChatHubState.handedToHub,
    this.cloudStored = false,
  });

  final String text;
  final String from;
  final bool isMine;
  final DateTime time;

  /// Only meaningful for [isMine] lines - see [ChatHubState].
  ChatHubState hubState;

  /// True only once `POST /api/mesh/chat` has returned 201 for this line.
  /// Never inferred from network reachability - see docs/05_PUBLIC_API.md.
  bool cloudStored;
}

/// One line this handset sent, remembered only long enough to recognise the
/// hub's echo of it.
class _SelfSend {
  const _SelfSend(this.text, this.at);

  final String text;
  final DateTime at;
}

// ---------------------------------------------------------------------------
// Service — WebSocket chat client for the Heltec WiFi-relay hub
//
// The Heltec module runs as a WiFi access point (default SSID "Aquan") and
// exposes a WebSocket server on its OWN port (`ws://<ap_ip>:81`, no path -
// see AqOneConfig.buoyWsUrl and docs/21_WEEK1_CONTRACT_FIXTURES.md). It is a
// separate WebSocketsServer instance from the HTTP server on port 80, so it
// has no `/ws` route - a client that connects to port 80 will never reach
// it. Connected clients are shown on a "client wheel" in the UI. An HTTP
// GET /history endpoint provides backfill on connect. Messages sent while
// offline are queued in SharedPreferences and flushed when the connection is
// restored.
// ---------------------------------------------------------------------------

class ChatService extends ChangeNotifier {
  ChatService({
    this.host = '192.168.4.1',
    required this.displayName,
    this.backendUrl = AqOneConfig.backendBaseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final http.Client _client;

  final String host;

  /// Cloud backend the dashboard reads from. Chat lines are relayed here in
  /// addition to the Heltec broadcast so a dispatcher on shore can see the
  /// mesh conversation without being on the Aquan WiFi.
  final String backendUrl;

  /// What this handset announces itself as on the hub. It MUST identify this
  /// boat and not this handset's point of view: the hub broadcasts the name
  /// verbatim to every other phone, and it is also how the roster and the
  /// echo guard below tell our own traffic apart. A generic "You" here made
  /// every boat on the hub announce the same name, which put every other
  /// fisher's message in our own bubble. Derive it with [displayNameFor].
  final String displayName;

  static const int maxMessageLength = 50;
  static const int _maxMessages = 50;
  static const Duration _messageRetention = Duration(hours: 24);

  /// How long a message we sent stays eligible to be recognised as the hub's
  /// echo of itself. Generous, because the flush path can lag a reconnect.
  static const Duration _echoWindow = Duration(seconds: 10);

  /// The boat name is what a fisher on another banca recognises over the
  /// radio, so it wins over the skipper's own name. Both are optional in the
  /// profile, hence the final fallback.
  static String displayNameFor(VesselIdentity identity) {
    for (final String candidate in <String>[
      identity.boat,
      identity.skipperName,
    ]) {
      final String trimmed = candidate.trim();
      if (trimmed.isNotEmpty) {
        return trimmed.length <= AqOneConfig.maxBoatBytes
            ? trimmed
            : trimmed.substring(0, AqOneConfig.maxBoatBytes);
      }
    }
    return 'Fisher';
  }

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnectTimer;

  final List<ChatMessage> _messages = [];
  final List<String> _clients = [];
  final List<String> _pendingQueue = [];

  /// Messages we put on the wire and have already drawn locally, kept so the
  /// hub's broadcast of them can be recognised and dropped. See [_isSelfEcho].
  final List<_SelfSend> _selfSends = [];

  /// Guards [_relayToBackend] against sending the same still-pending line
  /// twice while an earlier attempt for it is still in flight.
  final Set<ChatMessage> _relayInFlight = {};

  bool _connected = false;
  bool _connecting = false;
  bool _disposed = false;
  String? _lastError;

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  List<String> get clients => List.unmodifiable(_clients);
  bool get connected => _connected;
  bool get connecting => _connecting;
  String? get lastError => _lastError;
  int get pendingCount => _pendingQueue.length;

  Uri get _wsUri => EndpointGuard.buoyWs(host);
  Uri get _historyUri => EndpointGuard.buoyHistory(host);

  /// Starts the connection loop and loads persisted messages / queue.
  Future<void> start() async {
    await _loadQueue();
    await _loadMessages();
    _connect();
    unawaited(_retryPendingCloudRelays());
    // Reuses the hub reconnect loop to also retry any of this handset's own
    // lines that have not yet reached the cloud relay - the two networks
    // (buoy WiFi, phone internet) are independent, so a line can be stuck on
    // one leg while the other is fine.
    _reconnectTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (_disposed) return;
      if (!_connected && !_connecting) _connect();
      unawaited(_retryPendingCloudRelays());
    });
  }

  Future<void> _connect() async {
    if (_connecting || _disposed) return;
    _connecting = true;
    _lastError = null;
    _notify();

    try {
      await _subscription?.cancel();
      _subscription = null;

      final channel = WebSocketChannel.connect(_wsUri);
      _channel = channel;

      // Awaiting [ready] surfaces connection errors inside our try/catch
      // instead of letting them escape as unhandled async exceptions
      // (web_socket_channel 3.x reports failures on both the stream and
      // the ready future).
      await channel.ready;

      _subscription = channel.stream.listen(
        _onMessage,
        onError: (Object e) {
          _connected = false;
          _connecting = false;
          _lastError = _describeChatError(e);
          _notify();
        },
        onDone: () {
          _connected = false;
          _connecting = false;
          _notify();
        },
        cancelOnError: true,
      );

      // Announce display name so the wheel updates.
      _safeSend(jsonEncode({'type': 'hello', 'name': displayName}));

      _connected = true;
      _connecting = false;
      _notify();

      await _backfillHistory();
      await _flushQueue();
    } catch (e) {
      _connected = false;
      _connecting = false;
      _lastError = _describeChatError(e);
      _notify();
    }
  }

  // ----- Incoming messages ------------------------------------------------

  void _onMessage(dynamic data) {
    final String raw;
    if (data is String) {
      raw = data;
    } else if (data is List<int>) {
      raw = utf8.decode(data, allowMalformed: true);
    } else {
      raw = data.toString();
    }

    final dynamic json;
    try {
      json = jsonDecode(raw);
    } catch (_) {
      return;
    }

    if (json is! Map<String, dynamic>) return;

    switch (json['type'] as String?) {
      case 'clients':
        _clients
          ..clear()
          ..addAll(
              (json['list'] as List<dynamic>?)?.map((e) => e.toString()) ?? []);
        _notify();

      case 'msg':
        final name = json['from'] as String? ?? '?';
        final text = json['text'] as String? ?? '';
        if (text.isEmpty) return;
        // The hub broadcasts to every socket it holds, so a buoy running
        // firmware that does not skip the sender hands us back the message we
        // drew the moment the fisher hit send. Drawing it twice reads as the
        // message having been sent twice - the last thing you want a person
        // to believe about a call for help. Matching on (name, text, recency)
        // rather than on the name alone keeps a same-named boat's genuinely
        // separate message visible.
        if (name == displayName && _isSelfEcho(text)) return;
        // Attribution is by announced name only. An older handset that still
        // announces the generic "You" is a different boat, not us, and must
        // not land in our own bubble.
        _messages.add(ChatMessage(
          text: text,
          from: name,
          isMine: name == displayName,
          time: DateTime.now(),
        ));
        _trimMessages();
        _notify();

      case 'history':
        final list = json['messages'] as List<dynamic>?;
        if (list == null) break;
        _adoptHistory(list);
    }
  }

  /// Folds the hub's backlog into the scrollback.
  ///
  /// This used to clear [_messages] and take the backlog wholesale, which is
  /// unsafe now that the hub does not echo a line back to the phone that sent
  /// it: a message sent while offline lives only on this handset until the
  /// queue flushes, and wiping it would take it off the sender's screen while
  /// every other boat still saw it. So:
  ///
  /// * nothing on screen — take the lot; this phone just arrived.
  /// * every backlog line carries a time — take only other boats' lines newer
  ///   than our newest, i.e. exactly what was said while we were away. Our own
  ///   lines are never adopted, so buoy/phone clock skew cannot duplicate them.
  /// * any line came back untimed (the buoy had no clock yet) — take none.
  ///   Without a time there is no way to tell a missed message from one
  ///   already on screen, and showing it twice is worse than not backfilling.
  void _adoptHistory(List<dynamic> list) {
    final List<ChatMessage> backlog = [];
    bool everyLineTimed = true;

    for (final entry in list) {
      if (entry is! Map<String, dynamic>) continue;
      final String text = entry['text'] as String? ?? '';
      if (text.isEmpty) continue;
      final String from = entry['from'] as String? ?? '?';
      final DateTime? at = DateTime.tryParse(entry['time'] as String? ?? '');
      if (at == null) everyLineTimed = false;
      backlog.add(ChatMessage(
        text: text,
        from: from,
        isMine: from == displayName,
        time: at ?? DateTime.now(),
      ));
    }
    final List<ChatMessage>? merged = mergeHistory(
      _messages,
      backlog,
      everyLineTimed: everyLineTimed,
    );
    if (merged == null) return;

    _messages
      ..clear()
      ..addAll(merged);
    _trimMessages();
    _persistMessages();
    _notify();
  }

  /// The merge rules described on [_adoptHistory], as a pure function so they
  /// can be tested without a socket. Returns null when the backlog changes
  /// nothing and the scrollback should be left alone.
  static List<ChatMessage>? mergeHistory(
    List<ChatMessage> current,
    List<ChatMessage> backlog, {
    required bool everyLineTimed,
  }) {
    if (backlog.isEmpty) return null;
    if (current.isEmpty) return List<ChatMessage>.of(backlog);
    if (!everyLineTimed) return null;

    final DateTime newest = current.last.time;
    final List<ChatMessage> missed = backlog
        .where((ChatMessage m) => !m.isMine && m.time.isAfter(newest))
        .toList();
    if (missed.isEmpty) return null;
    return <ChatMessage>[...current, ...missed];
  }

  void _trimMessages() {
    final retained = retainRecentMessages(_messages);
    _messages
      ..clear()
      ..addAll(retained);
  }

  static List<ChatMessage> retainRecentMessages(
    Iterable<ChatMessage> messages, {
    DateTime? now,
  }) {
    final DateTime cutoff = (now ?? DateTime.now()).subtract(_messageRetention);
    final List<ChatMessage> retained = messages
        .where((ChatMessage message) => !message.time.isBefore(cutoff))
        .toList(growable: true);
    if (retained.length > _maxMessages) {
      retained.removeRange(0, retained.length - _maxMessages);
    }
    return retained;
  }

  /// POSTs one of this handset's own lines to the backend mesh chat endpoint.
  /// Only a `201` counts as "cloud relay stored" — see docs/05_PUBLIC_API.md.
  /// Any other outcome (timeout, non-201, no internet) leaves [msg] exactly
  /// as it was; it is never dropped, and [_retryPendingCloudRelays] will try
  /// it again on the next reconnect tick.
  Future<void> _relayToBackend(ChatMessage msg) async {
    if (msg.cloudStored || _relayInFlight.contains(msg)) return;
    _relayInFlight.add(msg);
    try {
      final response = await _client
          .post(
            EndpointGuard.backend(backendUrl, '/api/mesh/chat'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({'sender': msg.from, 'text': msg.text}),
          )
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 201) {
        msg.cloudStored = true;
        _persistMessages();
        _notify();
      }
    } catch (_) {
      // Network/host failure: honest state is "still unknown", not "failed
      // to send" — the hub/local queue above already carries the line.
    } finally {
      _relayInFlight.remove(msg);
    }
  }

  /// Re-attempts the cloud relay for every one of this handset's own lines
  /// that has not yet been confirmed `cloud relay stored`. Cheap to call
  /// often: [_relayToBackend] no-ops once a line is stored or already
  /// in flight, so a message that already succeeded costs nothing here.
  Future<void> _retryPendingCloudRelays() async {
    final List<ChatMessage> pending = _messages
        .where((ChatMessage m) => m.isMine && !m.cloudStored)
        .toList(growable: false);
    for (final ChatMessage msg in pending) {
      unawaited(_relayToBackend(msg));
    }
  }

  // ----- Outgoing messages ------------------------------------------------

  Future<void> sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    if (trimmed.length > maxMessageLength) {
      // Reject, never truncate: a truncated emergency-relevant sentence is
      // worse than one that visibly did not send.
      _lastError =
          'message is longer than $maxMessageLength characters - not sent';
      _notify();
      return;
    }

    final msg = ChatMessage(
      text: trimmed,
      from: displayName,
      isMine: true,
      time: DateTime.now(),
      hubState:
          _connected ? ChatHubState.handedToHub : ChatHubState.queuedLocally,
    );
    _messages.add(msg);
    _trimMessages();
    _persistMessages();
    _notify();

    if (_connected) {
      _sendChat(trimmed);
    } else {
      _pendingQueue.add(trimmed);
      _persistQueue();
    }

    unawaited(_relayToBackend(msg));
  }

  /// Puts one chat line on the wire and records it for [_isSelfEcho]. Every
  /// outgoing `msg` goes through here so no send path can forget to.
  bool _sendChat(String text) {
    if (!_connected || _channel == null) return false;
    final ok = _safeSend(jsonEncode({
      'type': 'msg',
      'from': displayName,
      'text': text,
    }));
    if (ok) {
      _selfSends.add(_SelfSend(text, DateTime.now()));
    }
    return ok;
  }

  /// Advances the oldest still-[ChatHubState.queuedLocally] message with this
  /// text to [ChatHubState.handedToHub] after [_flushQueue] puts it on the
  /// wire. Matches by text (FIFO), not identity, because the queue only ever
  /// stored raw strings — this is the same at-least-once/no-cross-hop-dedup
  /// limitation documented in docs/05_PUBLIC_API.md, not a new one.
  void _markHandedToHub(String text) {
    for (final ChatMessage m in _messages) {
      if (m.isMine &&
          m.text == text &&
          m.hubState == ChatHubState.queuedLocally) {
        m.hubState = ChatHubState.handedToHub;
        _persistMessages();
        _notify();
        return;
      }
    }
  }

  /// Whether [text] is the hub echoing back something we just sent, in which
  /// case it is already on screen. Consumes the record, so a fisher who sends
  /// the same word twice still sees it twice.
  bool _isSelfEcho(String text) {
    final DateTime cutoff = DateTime.now().subtract(_echoWindow);
    _selfSends.removeWhere((_SelfSend sent) => sent.at.isBefore(cutoff));
    final int index =
        _selfSends.indexWhere((_SelfSend sent) => sent.text == text);
    if (index < 0) return false;
    _selfSends.removeAt(index);
    return true;
  }

  // ----- History backfill -------------------------------------------------

  Future<void> _backfillHistory() async {
    try {
      final res =
          await _client.get(_historyUri).timeout(const Duration(seconds: 4));
      if (res.statusCode != 200) return;
      final dynamic json = jsonDecode(res.body);
      if (json is! Map<String, dynamic>) return;
      final list = json['messages'] as List<dynamic>?;
      if (list == null) return;
      _adoptHistory(list);
    } catch (_) {
      // Hub offline — not an error on mobile.
    }
  }

  // ----- Offline queue (SharedPreferences) --------------------------------

  Future<void> _flushQueue() async {
    if (_pendingQueue.isEmpty || !_connected) return;
    while (_pendingQueue.isNotEmpty && _connected) {
      final text = _pendingQueue.first;
      final sent = _sendChat(text);
      if (!sent) {
        break;
      }
      _pendingQueue.removeAt(0);
      _markHandedToHub(text);
      _persistQueue();
      // Small delay so the Heltec relay can keep up.
      await Future<void>.delayed(const Duration(milliseconds: 80));
    }
  }

  @visibleForTesting
  Future<void> flushQueueForTesting() => _flushQueue();

  @visibleForTesting
  void setConnectedForTesting(bool value) => _connected = value;

  Future<void> _loadQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _pendingQueue
        ..clear()
        ..addAll(prefs.getStringList('chat_pending_queue') ?? []);
    } catch (_) {}
  }

  Future<void> _persistQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('chat_pending_queue', _pendingQueue);
    } catch (_) {}
  }

  Future<void> _loadMessages() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString('chat_cached_messages');
      if (raw == null) return;
      final list = jsonDecode(raw) as List<dynamic>;
      _messages.clear();
      for (final entry in list) {
        if (entry is! Map<String, dynamic>) continue;
        // 'hub_state'/'cloud_stored' are absent on rows written before this
        // field existed. Defaulting to handedToHub/false is the honest
        // reading: those older lines were always sent immediately, and an
        // unknown cloud outcome must never be assumed stored.
        _messages.add(ChatMessage(
          text: entry['text'] as String? ?? '',
          from: entry['from'] as String? ?? '?',
          isMine: (entry['from'] as String?) == displayName,
          time: DateTime.tryParse(entry['time'] as String? ?? '') ??
              DateTime.now(),
          hubState: (entry['hub_state'] as String?) == 'queuedLocally'
              ? ChatHubState.queuedLocally
              : ChatHubState.handedToHub,
          cloudStored: entry['cloud_stored'] as bool? ?? false,
        ));
      }
      _trimMessages();
      _notify();
    } catch (_) {}
  }

  Future<void> _persistMessages() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final data = _messages
          .map((m) => {
                'text': m.text,
                'from': m.from,
                'time': m.time.toIso8601String(),
                'hub_state': m.hubState.name,
                'cloud_stored': m.cloudStored,
              })
          .toList();
      await prefs.setString('chat_cached_messages', jsonEncode(data));
    } catch (_) {}
  }

  // ----- Helpers ----------------------------------------------------------

  bool _safeSend(String data) {
    try {
      if (!_connected || _channel == null) return false;
      _channel?.sink.add(data);
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Turns a raw WebSocket/HTTP exception into text a fisher standing near
  /// the buoy can read. [lastError] is not shown anywhere in the UI yet, but
  /// it is public API on a service other screens may reasonably read from
  /// later, so it should never carry Dart's own exception text.
  static String _describeChatError(Object error) {
    final text = error.toString();
    if (text.contains('TimeoutException')) {
      return 'no reply from the chat hub';
    }
    if (text.contains('SocketException') ||
        text.contains('Connection refused') ||
        text.contains('Failed host lookup')) {
      return 'not connected to the Aquan WiFi hub';
    }
    if (text.contains('WebSocketChannelException') ||
        text.contains('WebSocketException')) {
      return 'chat connection dropped';
    }
    return 'could not connect to the chat hub';
  }

  /// Guards every `notifyListeners()` call in this class.
  ///
  /// Most call sites here run after an `await` (WebSocket connect, HTTP
  /// backfill, SharedPreferences I/O) or inside a stream callback - both can
  /// resume/fire after [dispose] has already run, e.g. when the fisherman
  /// backs out of chat while a connection attempt is still in flight.
  /// `ChangeNotifier.notifyListeners()` throws once disposed, so every call
  /// goes through this check instead of calling it directly.
  void _notify() {
    if (!_disposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _subscription?.cancel();
    _channel?.sink.close();
    super.dispose();
  }
}

// ---------------------------------------------------------------------------
// Avatars
// ---------------------------------------------------------------------------

/// First letter of [name], upper-cased. That letter is the entire avatar:
/// there are no profile pictures to fetch once this runs over LoRa.
String initialOf(String name) {
  final trimmed = name.trim();
  return trimmed.isEmpty ? '?' : trimmed[0].toUpperCase();
}

/// A stable colour per participant - the same name always lands on the same
/// hue, so a neighbour is recognisable before you read the letter. Matters
/// once LoRa makes the roster longer than a couple of boats, and two of them
/// share an initial. Top-level (rather than a private helper on the state)
/// so the bubble, wheel and header all derive avatars the same way instead
/// of each doing its own `name[0]`.
/// Caption shown under this handset's own outgoing lines: the honest facts
/// this handset actually knows, per docs/05_PUBLIC_API.md's truth rules.
/// Cloud confirmation (a real HTTP 201) outranks the hub leg, which has no
/// receipt at all - showing both at once would just repeat "not confirmed"
/// twice in different words.
String hubCloudStatusLabel(AppLocalizations t, ChatMessage msg) {
  if (msg.cloudStored) {
    return t.chatStatusSynced;
  }
  if (msg.hubState == ChatHubState.handedToHub) {
    return t.chatStatusSent;
  }
  return t.chatStatusQueued;
}

Color avatarColorOf(String name) {
  const palette = <Color>[
    Color(0xFF38BDF8),
    Color(0xFF34D399),
    Color(0xFFF59E0B),
    Color(0xFFF472B6),
    Color(0xFFA78BFA),
    Color(0xFF22D3EE),
  ];
  var hash = 0;
  for (final unit in name.trim().codeUnits) {
    hash = (hash * 31 + unit) & 0x7FFFFFFF;
  }
  return palette[hash % palette.length];
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

class Chathubb extends StatefulWidget {
  const Chathubb({super.key, required this.identity});

  /// Whose boat this is. Only the name is used, but taking the identity keeps
  /// the derivation ([ChatService.displayNameFor]) in one place rather than
  /// letting each call site invent its own fallback.
  final VesselIdentity identity;

  @override
  State<Chathubb> createState() => _ChathubbState();
}

class _ChathubbState extends State<Chathubb> {
  late final ChatService _service = ChatService(
    displayName: ChatService.displayNameFor(widget.identity),
  );
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scroll = ScrollController();
  bool _onAquan = false;
  Timer? _wifiPollTimer;

  @override
  void initState() {
    super.initState();
    _service.start();
    _checkWifi();
    // Poll WiFi status every 5 s.
    _wifiPollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted) _checkWifi();
    });
  }

  @override
  void dispose() {
    _wifiPollTimer?.cancel();
    _wifiPollTimer = null;
    _service.dispose();
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _checkWifi() async {
    bool onAq = false;
    try {
      final info = NetworkInfo();
      final name = await info.getWifiName();
      onAq = name?.contains('Aquan') == true;
    } catch (_) {}

    // Fallback: if the hub is reachable over HTTP we consider WiFi OK.
    if (!onAq) {
      try {
        final res = await http
            .get(EndpointGuard.buoyHistory(_service.host))
            .timeout(const Duration(seconds: 2));
        onAq = res.statusCode == 200;
      } catch (_) {}
    }

    if (mounted) setState(() => _onAquan = onAq);
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    await _service.sendMessage(text);
    await Future<void>.delayed(const Duration(milliseconds: 100));
    if (_scroll.hasClients) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
      );
    }
  }

  // ---- Build -------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return ListenableBuilder(
      listenable: _service,
      builder: (context, _) {
        return Scaffold(
          backgroundColor: isDark ? const Color(0xFF0F172A) : Colors.white,
          appBar: AppBar(
            backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
            elevation: 0,
            leading: IconButton(
              icon: Icon(Icons.arrow_back_rounded,
                  color: isDark ? Colors.white : Colors.black87),
              onPressed: () => Navigator.of(context).pop(),
            ),
            titleSpacing: 0,
            title: _buildHeaderTitle(isDark),
            actions: [
              Padding(
                padding: const EdgeInsets.only(right: 16),
                child: Tooltip(
                  message: _service.connected
                      ? 'Connected to Aquan'
                      : (_onAquan ? 'On Aquan - connecting…' : 'Not on Aquan'),
                  child: Icon(
                    Icons.wifi,
                    color: (_service.connected || _onAquan)
                        ? const Color(0xFF16A34A)
                        : const Color(0xFF94A3B8),
                    size: 22,
                  ),
                ),
              ),
            ],
          ),
          body: Column(
            children: [
              // Clients wheel
              if (_service.clients.isNotEmpty) _buildClientWheel(isDark),
              // Messages
              Expanded(child: _buildMessageList(isDark)),
              // Input
              _buildInputBar(isDark),
            ],
          ),
        );
      },
    );
  }

  // ---- Header ------------------------------------------------------------

  /// Everyone on the hub roster except this handset.
  List<String> get _peers => _service.clients
      .where((String name) => name != _service.displayName)
      .toList(growable: false);

  /// Who you are talking to. One peer shows their name; a fuller roster shows
  /// the first two and a count, the way a group thread does, so the title
  /// never overflows the app bar on a phone.
  String get _headerName {
    final peers = _peers;
    if (peers.isEmpty) return 'Chat';
    if (peers.length == 1) return peers.first;
    if (peers.length == 2) return '${peers[0]}, ${peers[1]}';
    return '${peers[0]}, ${peers[1]} +${peers.length - 2}';
  }

  Widget _buildHeaderTitle(bool isDark) {
    final peers = _peers;
    final String status;
    if (!_service.connected) {
      status = _onAquan ? 'Connecting…' : 'Offline';
    } else if (peers.isEmpty) {
      status = 'Waiting for others…';
    } else if (peers.length == 1) {
      status = 'On the mesh';
    } else {
      status = '${peers.length} on the mesh';
    }

    return Row(
      children: [
        if (peers.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(right: 10),
            child: CircleAvatar(
              radius: 18,
              backgroundColor: avatarColorOf(peers.first),
              child: Text(
                initialOf(peers.first),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
            ),
          ),
        Expanded(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _headerName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: isDark ? Colors.white : Colors.black87,
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                ),
              ),
              Text(
                status,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: _service.connected
                      ? const Color(0xFF16A34A)
                      : (isDark ? Colors.white54 : Colors.black45),
                  fontWeight: FontWeight.w500,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ---- Client wheel ------------------------------------------------------

  Widget _buildClientWheel(bool isDark) {
    // The hub's roster already contains this handset under its own name -
    // it is added when we send 'hello'. No need to prepend a literal "You":
    // displayName is now derived from the vessel identity (see
    // ChatService.displayNameFor), so a name never collides across boats.
    final users = _service.clients;
    return Container(
      height: 92,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: users.length == 1
          ? Center(
              child: Text(
                'Waiting for others to join…',
                style: TextStyle(
                  color: isDark ? Colors.white54 : Colors.black38,
                  fontSize: 13,
                ),
              ),
            )
          : ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: users.length,
              separatorBuilder: (context, index) => const SizedBox(width: 16),
              itemBuilder: (context, index) {
                final name = users[index];
                final isSelf = name == _service.displayName;
                return Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircleAvatar(
                      radius: 22,
                      backgroundColor: isSelf
                          ? const Color(0xFF0F69C9)
                          : avatarColorOf(name),
                      child: Text(
                        initialOf(name),
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      name,
                      style: TextStyle(
                        fontSize: 12,
                        color: isDark ? Colors.white70 : Colors.black54,
                      ),
                    ),
                  ],
                );
              },
            ),
    );
  }

  // ---- Messages ----------------------------------------------------------

  Widget _buildMessageList(bool isDark) {
    if (_service.messages.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.waves_rounded,
              size: 48,
              color: isDark ? Colors.white24 : Colors.black12,
            ),
            const SizedBox(height: 12),
            Text(
              'AqOne',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: isDark ? Colors.white38 : Colors.black26,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'No messages yet. Say hi!',
              style: TextStyle(
                fontSize: 13,
                color: isDark ? Colors.white38 : Colors.black26,
              ),
            ),
          ],
        ),
      );
    }
    return ListView.builder(
      controller: _scroll,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      itemCount: _service.messages.length,
      itemBuilder: (context, index) {
        final msg = _service.messages[index];
        return _buildBubble(msg, isDark);
      },
    );
  }

  Widget _buildBubble(ChatMessage msg, bool isDark) {
    final isMine = msg.isMine;
    final bg = isMine
        ? const Color(0xFF0F69C9)
        : (isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9));
    final fg = isMine ? Colors.white : (isDark ? Colors.white : Colors.black87);
    final align = isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    final radius = BorderRadius.only(
      topLeft: const Radius.circular(16),
      topRight: const Radius.circular(16),
      bottomLeft: Radius.circular(isMine ? 16 : 4),
      bottomRight: Radius.circular(isMine ? 4 : 16),
    );

    final initial = initialOf(msg.from);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment:
            isMine ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isMine)
            Padding(
              padding: const EdgeInsets.only(right: 8, top: 4),
              child: CircleAvatar(
                radius: 14,
                backgroundColor: avatarColorOf(msg.from),
                child: Text(
                  initial,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          Flexible(
            child: Column(
              crossAxisAlignment: align,
              children: [
                if (!isMine)
                  Padding(
                    padding: const EdgeInsets.only(left: 4, bottom: 2),
                    child: Text(
                      msg.from,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: isDark ? Colors.white54 : Colors.black45,
                      ),
                    ),
                  ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: bg,
                    borderRadius: radius,
                  ),
                  child: Text(
                    msg.text,
                    style: TextStyle(color: fg, fontSize: 15, height: 1.3),
                  ),
                ),
                Padding(
                  padding: EdgeInsets.only(
                    top: 2,
                    left: isMine ? 0 : 4,
                    right: isMine ? 4 : 0,
                  ),
                  child: Text(
                    isMine
                        ? '${msg.time.hour.toString().padLeft(2, '0')}:${msg.time.minute.toString().padLeft(2, '0')} · '
                            '${hubCloudStatusLabel(AppLocalizations.of(context), msg)}'
                        : '${msg.time.hour.toString().padLeft(2, '0')}:${msg.time.minute.toString().padLeft(2, '0')}',
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? Colors.white30 : Colors.black26,
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (isMine) const SizedBox(width: 8),
        ],
      ),
    );
  }

  // ---- Input bar ---------------------------------------------------------

  Widget _buildInputBar(bool isDark) {
    return Container(
      padding: EdgeInsets.only(
        left: 12,
        right: 8,
        top: 8,
        bottom: MediaQuery.of(context).padding.bottom + 8,
      ),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              constraints: const BoxConstraints(maxHeight: 100),
              decoration: BoxDecoration(
                color:
                    isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(24),
              ),
              child: TextField(
                controller: _controller,
                textCapitalization: TextCapitalization.sentences,
                maxLines: null,
                maxLength: ChatService.maxMessageLength,
                style: TextStyle(
                  color: isDark ? Colors.white : Colors.black87,
                  fontSize: 15,
                ),
                // Shown before sending, not just after a rejection - a fisher
                // composing an emergency-relevant sentence should see the
                // 50-character ceiling coming, not discover it mid-word.
                buildCounter: (
                  context, {
                  required int currentLength,
                  required bool isFocused,
                  int? maxLength,
                }) {
                  return Text(
                    AppLocalizations.of(context).chatCharacterLimitLabel(
                      currentLength,
                      maxLength ?? ChatService.maxMessageLength,
                    ),
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? Colors.white38 : Colors.black38,
                    ),
                  );
                },
                decoration: InputDecoration(
                  border: InputBorder.none,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                  hintText: AppLocalizations.of(context).chatHint,
                  hintStyle: TextStyle(
                    color: isDark ? Colors.white38 : Colors.black26,
                  ),
                ),
                onSubmitted: (_) => _send(),
              ),
            ),
          ),
          const SizedBox(width: 6),
          IconButton(
            onPressed: _send,
            icon: const Icon(Icons.send_rounded),
            color: const Color(0xFF0F69C9),
            splashRadius: 24,
          ),
        ],
      ),
    );
  }
}

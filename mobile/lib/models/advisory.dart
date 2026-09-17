import 'package:flutter/material.dart';

/// How urgent an advisory is. Order matters: [severity] drives list sorting.
enum AdvisoryPriority {
  emergency('Emergency', 4, Color(0xFFDC2626)),
  warning('Warning', 3, Color(0xFFF59E0B)),
  information('Information', 2, Color(0xFF0F69C9)),
  community('Community', 1, Color(0xFF10B981)),
  unknown('Notice', 0, Color(0xFF6B7280));

  const AdvisoryPriority(this.label, this.severity, this.color);

  final String label;
  final int severity;
  final Color color;

  static AdvisoryPriority fromWire(String? value) {
    switch (value?.toLowerCase().trim()) {
      case 'emergency':
        return AdvisoryPriority.emergency;
      case 'warning':
        return AdvisoryPriority.warning;
      case 'information':
        return AdvisoryPriority.information;
      case 'community':
        return AdvisoryPriority.community;
      default:
        return AdvisoryPriority.unknown;
    }
  }
}

/// A published notice from the MDRRMO or LGU.
class Advisory {
  const Advisory({
    this.id,
    required this.title,
    required this.description,
    required this.priority,
    required this.municipality,
    this.source,
    this.revision,
    this.category,
    this.publishDate,
    this.expirationDate,
    this.imageUrl,
    this.imageAsset,
    this.isOfficial = true,
    this.byline,
  });

  final int? id;
  final String title;
  final String description;
  final AdvisoryPriority priority;
  final String municipality;
  final String? source;
  final int? revision;
  final String? category;
  final DateTime? publishDate;
  final DateTime? expirationDate;

  /// Photo attached by whoever published the advisory - a damaged pier, a
  /// posted bulletin. Network URL, so it needs a graceful failure: the reader
  /// is frequently offshore with no signal and the text must survive without
  /// it.
  final String? imageUrl;

  /// Bundled asset instead of a URL. Only for advisories the app itself
  /// carries, which is why the wire format has no equivalent - a backend
  /// cannot reference an image inside the APK.
  final String? imageAsset;

  /// False for anything AqOne generated rather than the MDRRMO or LGU.
  ///
  /// This screen is where a fisherman reads official instructions, so
  /// anything that is not one must not be able to pass as one. §3.3 of the
  /// system design keeps human authority explicit; an app that quietly speaks
  /// in the LGU's voice erodes exactly the trust the safety features depend
  /// on. Drives a visibly different card, not a footnote.
  final bool isOfficial;

  /// Who published it, when that is not a municipality. Shown in place of
  /// [municipality] for unofficial notices.
  final String? byline;

  /// Whether this advisory is still in force.
  ///
  /// For exact instants (hours/minutes/seconds non-zero), expiry honors the
  /// exact instant. For date-only calendar days, it extends to 23:59:59 of that
  /// day.
  /// Missing expiry on official advisories is bounded by a 48-hour retention
  /// policy from publish date rather than being silently immortal.
  bool get isActive {
    final now = DateTime.now();
    final expiry = expirationDate;
    if (expiry != null) {
      if (expiry.hour != 0 || expiry.minute != 0 || expiry.second != 0) {
        return expiry.isAfter(now);
      }
      final endOfDay = DateTime(expiry.year, expiry.month, expiry.day, 23, 59, 59);
      return endOfDay.isAfter(now);
    }
    if (!isOfficial) {
      return true;
    }
    final effectivePub = publishDate ?? now;
    final maxRetention = effectivePub.add(const Duration(hours: 48));
    return maxRetention.isAfter(now);
  }

  static Advisory? tryParse(Object? value) {
    if (value is! Map) {
      return null;
    }
    final title = value['title'];
    if (title is! String || title.trim().isEmpty) {
      return null;
    }
    final description = value['description'];
    final municipality = value['municipality'];
    final category = value['category'];
    final int? id = _id(value['id']);
    final String? source = _text(value['source'] ?? value['src']);
    final int? revision = _int(value['revision'] ?? value['rev']);
    final bool isOfficial = value['is_official'] as bool? ??
        (source != null && source.toLowerCase().contains('research') ? false : true);

    return Advisory(
      id: id,
      title: title.trim(),
      description: description is String ? description.trim() : '',
      priority: AdvisoryPriority.fromWire(value['priority'] as String?),
      municipality: municipality is String && municipality.trim().isNotEmpty
          ? municipality.trim()
          : 'All',
      source: source,
      revision: revision,
      category: category is String && category.trim().isNotEmpty
          ? category.trim()
          : null,
      publishDate: _date(value['publish_date'] ?? value['iss']),
      expirationDate: _date(value['expiration_date'] ?? value['exp']),
      imageUrl: _text(value['image_url']) ?? _text(value['cover_image']),
      isOfficial: isOfficial,
      byline: _text(value['byline']),
    );
  }

  static int? _id(Object? value) {
    if (value is int) return value;
    if (value is String) return int.tryParse(value.trim());
    return null;
  }

  static int? _int(Object? value) {
    if (value is int) return value;
    if (value is String) return int.tryParse(value.trim());
    return null;
  }

  static String? _text(Object? value) {
    if (value is! String) {
      return null;
    }
    final String trimmed = value.trim();
    return trimmed.isEmpty ? null : trimmed;
  }

  static DateTime? _date(Object? value) {
    if (value == null) return null;
    if (value is int) {
      if (value <= 0) return null;
      return DateTime.fromMillisecondsSinceEpoch(value * 1000, isUtc: true).toLocal();
    }
    if (value is! String || value.trim().isEmpty) {
      return null;
    }
    final trimmed = value.trim();
    return DateTime.tryParse(trimmed);
  }

  /// Parses, drops expired entries, and sorts by urgency then recency.
  static List<Advisory> parseList(Object? decoded) {
    if (decoded is String) {
      throw const FormatException('Expected decoded JSON Map or List, not raw String');
    }
    final rows = decoded is Map && decoded['advisories'] is List
        ? decoded['advisories'] as List
        : decoded is List
            ? decoded
            : const <Object?>[];

    final advisories = rows
        .map(Advisory.tryParse)
        .whereType<Advisory>()
        .where((advisory) => advisory.isActive)
        .toList();

    advisories.sort((a, b) {
      if (a.priority.severity != b.priority.severity) {
        return b.priority.severity.compareTo(a.priority.severity);
      }
      final dateA = a.publishDate ?? DateTime(1970);
      final dateB = b.publishDate ?? DateTime(1970);
      return dateB.compareTo(dateA);
    });
    return advisories;
  }
}

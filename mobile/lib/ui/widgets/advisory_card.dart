import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/l10n_fallback.dart';
import '../../data/welcome_advisory.dart';
import '../../l10n/app_localizations.dart';
import '../../models/advisory.dart';

/// One advisory, used both for the Home preview and in the full list.
class AdvisoryCard extends StatelessWidget {
  const AdvisoryCard({
    super.key,
    required this.advisory,
    this.remaining = 0,
    this.onViewAll,
    this.maxDescriptionLines = 3,
    this.showImage = true,
  });

  final Advisory advisory;

  /// How many further advisories exist, for the preview footer.
  final int remaining;

  final VoidCallback? onViewAll;
  final int maxDescriptionLines;

  /// False on Home, where this is a preview above the SOS controls and a
  /// 4:3 photo would push them down the screen.
  final bool showImage;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final t = AppLocalizations.of(context);
    final priority = advisory.priority;
    final bool official = advisory.isOfficial;
    // The welcome note is carried by the app, so its text comes from the
    // ARB files; everything else is published text shown as written.
    final bool welcome = identical(advisory, WelcomeAdvisory.instance);

    // An unofficial notice must not be mistakable for an MDRRMO instruction
    // at a glance, on a phone, in sunlight. A tinted surface and a dashed-
    // feeling border do more work here than any wording can.
    final Color unofficialTint =
        isDark ? const Color(0xFF14313F) : const Color(0xFFEFF8FF);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: official
            ? (isDark ? const Color(0xFF1E293B) : Colors.white)
            : unofficialTint,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: official
              ? (isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0))
              : const Color(0xFF0F69C9).withValues(alpha: 0.45),
          width: official ? 1 : 1.5,
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.04),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: official
                      ? priority.color.withValues(alpha: 0.15)
                      : const Color(0xFF0F69C9).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  official ? priority.label(t).toUpperCase() : t.advisoryAppNotice,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                    color: official ? priority.color : const Color(0xFF0F69C9),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  welcome
                      ? t.welcomeAdvisoryByline
                      : advisory.byline ??
                          (advisory.municipality == 'All'
                              ? t.advisoryAllAreas
                              : advisory.municipality),
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    color: isDark ? Colors.white54 : const Color(0xFF64748B),
                  ),
                ),
              ),
              if (advisory.publishDate != null)
                Text(
                  _shortDate(context, advisory.publishDate!),
                  style: TextStyle(
                    fontSize: 12,
                    color: isDark ? Colors.white54 : const Color(0xFF64748B),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            welcome ? t.welcomeAdvisoryTitle : advisory.title,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w800,
              height: 1.3,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
            ),
          ),
          if (showImage &&
              (advisory.imageAsset != null ||
                  advisory.imageUrl != null)) ...<Widget>[
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: AspectRatio(
                aspectRatio: 4 / 3,
                child: _AdvisoryImage(
                  assetPath: advisory.imageAsset,
                  url: advisory.imageUrl,
                  isDark: isDark,
                ),
              ),
            ),
          ],
          if (advisory.description.isNotEmpty) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              welcome ? t.welcomeAdvisoryBody : advisory.description,
              maxLines: maxDescriptionLines,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 16,
                height: 1.4,
                color: isDark ? Colors.white70 : const Color(0xFF475569),
              ),
            ),
          ],
          if (!official) ...<Widget>[
            const SizedBox(height: 10),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Icon(
                  Icons.info_outline_rounded,
                  size: 13,
                  color: isDark ? Colors.white54 : const Color(0xFF64748B),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    t.advisoryAppNoticeBody,
                    style: TextStyle(
                      fontSize: 16,
                      height: 1.35,
                      color: isDark ? Colors.white54 : const Color(0xFF64748B),
                    ),
                  ),
                ),
              ],
            ),
          ],
          if (advisory.expirationDate != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              t.advisoryInForceUntil(
                _shortDate(context, advisory.expirationDate!),
              ),
              style: TextStyle(
                fontSize: 12,
                fontStyle: FontStyle.italic,
                color: isDark ? Colors.white54 : const Color(0xFF64748B),
              ),
            ),
          ],
          if (onViewAll != null) ...<Widget>[
            const SizedBox(height: 12),
            InkWell(
              onTap: onViewAll,
              child: Row(
                children: <Widget>[
                  Text(
                    remaining > 0
                        ? t.advisoryViewAllMore(remaining)
                        : t.advisoryViewAll,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: priority.color,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    Icons.arrow_forward_rounded,
                    size: 15,
                    color: priority.color,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }


  static String _shortDate(BuildContext context, DateTime value) =>
      DateFormat('d MMM', dateLocaleFor(Localizations.localeOf(context)))
          .format(value);
}

/// Advisory photo, from the bundle or the network.
///
/// A network image has to fail well: the reader is often offshore with no
/// signal, and an advisory whose text is hidden behind a broken image is
/// worse than one with no image at all. Failures collapse to a small caption
/// rather than an error box, and the words above it stay readable.
class _AdvisoryImage extends StatelessWidget {
  const _AdvisoryImage({
    required this.assetPath,
    required this.url,
    required this.isDark,
  });

  final String? assetPath;
  final String? url;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final String? asset = assetPath;
    if (asset != null) {
      return Image.asset(
        asset,
        fit: BoxFit.cover,
        errorBuilder: (context, __, ___) => _unavailable(context),
      );
    }
    return Image.network(
      url!,
      fit: BoxFit.cover,
      errorBuilder: (context, __, ___) => _unavailable(context),
      loadingBuilder: (
        BuildContext context,
        Widget child,
        ImageChunkEvent? progress,
      ) {
        if (progress == null) {
          return child;
        }
        return ColoredBox(
          color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
          child: const Center(
            child: SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
        );
      },
    );
  }

  Widget _unavailable(BuildContext context) {
    return ColoredBox(
      color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
      child: Center(
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(
              Icons.image_not_supported_outlined,
              size: 15,
              color: isDark ? Colors.white38 : const Color(0xFF94A3B8),
            ),
            const SizedBox(width: 6),
            Text(
              AppLocalizations.of(context).advisoryPhotoOffline,
              style: TextStyle(
                fontSize: 12,
                color: isDark ? Colors.white38 : const Color(0xFF94A3B8),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

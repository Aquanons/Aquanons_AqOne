import 'package:flutter/material.dart';

import '../../core/tokens.dart';
import '../../l10n/app_localizations.dart';
import '../../models/nearby_sos.dart';

class NearbyHelpBanner extends StatelessWidget {
  const NearbyHelpBanner({
    super.key,
    required this.items,
    required this.hasFix,
    required this.onTap,
  });

  final List<NearbySos> items;
  final bool hasFix;
  final VoidCallback onTap;

  static const Color _danger = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    final t = AppLocalizations.of(context);
    final first = items.first;
    final String distanceLine;
    if (!hasFix) {
      distanceLine = t.nearbyHelpDistanceUnknown;
    } else {
      distanceLine = t.nearbyHelpAway(NearbySos.distanceText(first.distanceKm, t));
    }
    final extra = items.length - 1;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AqRadius.card),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: _danger.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AqRadius.card),
            border: Border.all(color: _danger, width: 1.5),
          ),
          child: Row(
            children: <Widget>[
              Container(
                width: 32,
                height: 32,
                decoration: const BoxDecoration(
                  color: _danger,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.warning_amber_rounded,
                  color: Colors.white,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      '${t.nearbyHelpTitle} - $distanceLine',
                      style: const TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w800,
                        color: _danger,
                      ),
                    ),
                    if (extra > 0)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          t.nearbyHelpMore(extra),
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: _danger,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: _danger),
            ],
          ),
        ),
      ),
    );
  }
}

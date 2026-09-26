import 'package:flutter/material.dart';

import '../../core/tokens.dart';
import '../../l10n/app_localizations.dart';
import '../../models/fisher_sos_situation.dart';
import '../../models/sos_record.dart';

class SosStatusCard extends StatelessWidget {
  const SosStatusCard({super.key, required this.record});

  final SosRecord record;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);
    final situation = FisherSosSituation.of(record);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AqSpace.base),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AqRadius.card),
        border: Border.all(color: palette.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Icon(situation.icon, color: situation.color, size: 28),
              ),
              const SizedBox(width: AqSpace.sm),
              Expanded(
                child: Text(
                  situation.title(t),
                  style: TextStyle(
                    color: palette.primaryText,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AqSpace.xs),
          Text(
            situation.description(t),
            style: TextStyle(
              color: palette.secondaryText,
              fontSize: 16,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

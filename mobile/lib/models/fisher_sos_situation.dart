import 'package:flutter/material.dart';

import '../core/tokens.dart';
import '../l10n/app_localizations.dart';
import 'delivery_policy.dart';
import 'delivery_state.dart';
import 'sos_record.dart';

enum FisherSosSituation {
  notSentYet(Icons.schedule_rounded, AqColors.warning),
  podHasIt(Icons.sync_rounded, AqColors.connectivity),
  podNotConfirmed(Icons.sync_problem_rounded, AqColors.warning),
  rescueCentreHasIt(Icons.mark_email_read_rounded, AqColors.info),
  helpComing(Icons.directions_boat_rounded, AqColors.success),
  cancelling(Icons.undo_rounded, AqColors.warning),
  cancelled(Icons.cancel_outlined, AqColors.slateText),
  closed(Icons.task_alt_rounded, AqColors.success);

  const FisherSosSituation(this.icon, this.color);

  final IconData icon;
  final Color color;

  static FisherSosSituation of(SosRecord record, {DateTime? now}) {
    if (record.resolvedAt != null) return closed;
    if (record.fisherReply == 2 && record.fisherReplySynced) return cancelled;
    if (record.fisherReply == 2) return cancelling;
    if (record.etaAt != null || record.state == DeliveryState.acknowledged) {
      return helpComing;
    }
    if (record.state == DeliveryState.delivered) return rescueCentreHasIt;
    if (record.state == DeliveryState.relayed) {
      final relayedAt = record.relayedAt;
      if (relayedAt != null &&
          (now ?? DateTime.now()).toUtc().difference(
                    DateTime.fromMillisecondsSinceEpoch(
                      relayedAt * 1000,
                      isUtc: true,
                    ),
                  ) >=
              podDeliveryDeadline) {
        return podNotConfirmed;
      }
      return podHasIt;
    }
    return notSentYet;
  }
}

extension FisherSosSituationL10n on FisherSosSituation {
  String title(AppLocalizations t) => switch (this) {
        FisherSosSituation.notSentYet => t.deliveryStateSavedTitle,
        FisherSosSituation.podHasIt ||
        FisherSosSituation.podNotConfirmed =>
          t.deliveryStateRelayedTitle,
        FisherSosSituation.rescueCentreHasIt => t.deliveryStateDeliveredTitle,
        FisherSosSituation.helpComing => t.deliveryStateAcknowledgedTitle,
        FisherSosSituation.cancelling => t.standDownPendingTitle,
        FisherSosSituation.cancelled => t.standDownTitle,
        FisherSosSituation.closed => t.resolvedTitle,
      };

  String description(AppLocalizations t) => switch (this) {
        FisherSosSituation.notSentYet => t.deliveryStateSavedDescription,
        FisherSosSituation.podHasIt => t.deliveryStateRelayedDescription,
        FisherSosSituation.podNotConfirmed => t.sosPodNotConfirmed,
        FisherSosSituation.rescueCentreHasIt =>
          t.deliveryStateDeliveredDescription,
        FisherSosSituation.helpComing => t.deliveryStateAcknowledgedDescription,
        FisherSosSituation.cancelling => t.standDownPendingDescription,
        FisherSosSituation.cancelled => t.standDownDescription,
        FisherSosSituation.closed => t.resolvedDescription,
      };
}

import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../models/advisory.dart';
import '../services/venture_feeds.dart';
import 'widgets/advisory_card.dart';

/// Published advisories from the MDRRMO and LGU.
///
/// Sorted most urgent first, then most recent. Expired notices are filtered
/// out, treating the expiration date as inclusive.
class AdvisoriesPage extends StatefulWidget {
  const AdvisoriesPage({
    super.key,
    required this.feeds,
    this.bottomInset = 0,
  });

  final VentureFeeds feeds;
  final double bottomInset;

  @override
  State<AdvisoriesPage> createState() => _AdvisoriesPageState();
}

class _AdvisoriesPageState extends State<AdvisoriesPage> {
  List<Advisory> _advisories = const <Advisory>[];
  bool _loading = true;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() => _loading = true);
    }
    final advisories = await widget.feeds.advisories();
    if (!mounted) {
      return;
    }
    setState(() {
      _loading = false;
      // Distinguish "the request failed" from "there are none right now".
      // Showing "no advisories" after a network error would imply an
      // all-clear that nobody actually gave.
      _failed = advisories == null;
      if (advisories != null) {
        _advisories = advisories;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor:
          isDark ? const Color(0xFF0F172A) : const Color(0xFFF4F8FA),
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          onRefresh: _load,
          child: _buildBody(isDark),
        ),
      ),
    );
  }

  Widget _buildBody(bool isDark) {
    final t = AppLocalizations.of(context);
    if (_loading && _advisories.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    return ListView(
      padding: EdgeInsets.fromLTRB(20, 20, 20, 32 + widget.bottomInset),
      children: <Widget>[
        Text(
          t.navAdvisories,
          style: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w900,
            color: isDark ? Colors.white : const Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          t.advisoriesSubtitle,
          style: TextStyle(
            fontSize: 13,
            color: isDark ? Colors.white70 : const Color(0xFF64748B),
          ),
        ),
        const SizedBox(height: 20),
        if (_failed && _advisories.isEmpty)
          _Placeholder(
            icon: Icons.cloud_off_rounded,
            title: t.advisoriesLoadFailedTitle,
            body: t.advisoriesLoadFailedBody,
            isDark: isDark,
          )
        else if (_advisories.isEmpty)
          _Placeholder(
            icon: Icons.inbox_rounded,
            title: t.advisoriesEmptyTitle,
            body: t.advisoriesEmptyBody,
            isDark: isDark,
          )
        else ...<Widget>[
          if (_failed)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                t.advisoriesStaleList,
                style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: isDark ? Colors.white54 : const Color(0xFF64748B),
                ),
              ),
            ),
          for (final advisory in _advisories)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: AdvisoryCard(
                advisory: advisory,
                maxDescriptionLines: 6,
              ),
            ),
        ],
      ],
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({
    required this.icon,
    required this.title,
    required this.body,
    required this.isDark,
  });

  final IconData icon;
  final String title;
  final String body;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48),
      child: Column(
        children: <Widget>[
          Icon(
            icon,
            size: 40,
            color: isDark ? Colors.white38 : const Color(0xFF94A3B8),
          ),
          const SizedBox(height: 12),
          Text(
            title,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: isDark ? Colors.white70 : const Color(0xFF334155),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            body,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 13,
              color: isDark ? Colors.white54 : const Color(0xFF64748B),
            ),
          ),
        ],
      ),
    );
  }
}

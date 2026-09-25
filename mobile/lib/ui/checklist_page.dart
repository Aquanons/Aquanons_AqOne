import 'package:flutter/material.dart';

import '../core/tokens.dart';
import '../data/checklist_store.dart';
import '../l10n/app_localizations.dart';
import '../models/checklist_item.dart';
import '../services/location_service.dart';

/// Trip gear checklist as its own page: a list, a way to add/remove rows,
/// and nothing hidden behind a popover that a map gesture could dismiss by
/// accident.
class ChecklistPage extends StatefulWidget {
  const ChecklistPage({
    super.key,
    required this.checklist,
    this.location,
  });

  final ChecklistStore checklist;
  final LocationService? location;

  @override
  State<ChecklistPage> createState() => _ChecklistPageState();
}

class _ChecklistPageState extends State<ChecklistPage> {
  final TextEditingController _newItem = TextEditingController();
  List<ChecklistItem> _items = const <ChecklistItem>[];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _newItem.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final rows = await widget.checklist.all();
    if (!mounted) {
      return;
    }
    setState(() {
      _items = rows;
      _loading = false;
    });
  }

  Future<void> _addItem() async {
    final text = _newItem.text.trim();
    if (text.isEmpty) {
      return;
    }
    _newItem.clear();
    await widget.checklist.add(text);
    await _load();
  }

  Future<void> _toggle(ChecklistItem item, bool value) async {
    // Optimistic - a checkbox that lags behind the tap feels broken.
    setState(() {
      _items = _items
          .map((i) => i.id == item.id ? i.copyWith(isDone: value) : i)
          .toList(growable: false);
    });
    await widget.checklist.setDone(item.id, value);
  }

  Future<void> _delete(ChecklistItem item) async {
    setState(() => _items = _items.where((i) => i.id != item.id).toList());
    await widget.checklist.delete(item.id);
  }

  Future<void> _confirmNewTrip() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(AppLocalizations.of(ctx).checklistNewTripTitle),
        content: Text(AppLocalizations.of(ctx).checklistNewTripBody),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(AppLocalizations.of(ctx).actionCancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(AppLocalizations.of(ctx).checklistStartNewTrip),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }
    (widget.location ?? LocationService()).warmUp();
    await widget.checklist.resetForNewTrip();
    await _load();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).checklistResetSnackBar),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final doneCount = _items.where((i) => i.isDone).length;
    return Scaffold(
      backgroundColor: palette.canvas,
      appBar: AppBar(
        backgroundColor: palette.surface,
        elevation: 0,
        title: Text(
          AppLocalizations.of(context).checklistTripTitle,
          style: TextStyle(color: palette.primaryText, fontWeight: FontWeight.w700),
        ),
        iconTheme: IconThemeData(color: palette.primaryText),
        actions: <Widget>[
          TextButton.icon(
            onPressed: _items.isEmpty ? null : _confirmNewTrip,
            icon: const Icon(Icons.refresh_rounded, size: 18),
            label: Text(AppLocalizations.of(context).checklistNewTripButton),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: <Widget>[
                    if (_items.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(
                          AqSpace.screen,
                          AqSpace.sm,
                          AqSpace.screen,
                          0,
                        ),
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            AppLocalizations.of(context)
                                .checklistPackedLabel(doneCount, _items.length),
                            style: TextStyle(
                                fontSize: 12.5, color: palette.dimText),
                          ),
                        ),
                      ),
                    Expanded(
                      child: _items.isEmpty
                          ? ListView(
                              children: <Widget>[
                                const SizedBox(height: 120),
                                Center(
                                  child: Text(
                                    AppLocalizations.of(context).checklistEmpty,
                                    style: TextStyle(color: palette.dimText),
                                  ),
                                ),
                              ],
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.all(AqSpace.screen),
                              itemCount: _items.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: AqSpace.sm),
                              itemBuilder: (context, index) => _ChecklistTile(
                                item: _items[index],
                                palette: palette,
                                onToggle: (value) =>
                                    _toggle(_items[index], value),
                                onDelete: () => _delete(_items[index]),
                              ),
                            ),
                    ),
                    Padding(
                      padding: EdgeInsets.only(
                        left: AqSpace.screen,
                        right: AqSpace.screen,
                        top: AqSpace.sm,
                        bottom: AqSpace.screen + MediaQuery.of(context).padding.bottom,
                      ),
                      child: Row(
                        children: <Widget>[
                          Expanded(
                            child: TextField(
                              controller: _newItem,
                              decoration: InputDecoration(
                                isDense: true,
                                hintText:
                                    AppLocalizations.of(context).checklistAddItem,
                                border: const OutlineInputBorder(),
                              ),
                              onSubmitted: (_) => _addItem(),
                            ),
                          ),
                          const SizedBox(width: AqSpace.sm),
                          FilledButton(
                            onPressed: _addItem,
                            child: const Icon(Icons.add_rounded),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

class _ChecklistTile extends StatelessWidget {
  const _ChecklistTile({
    required this.item,
    required this.palette,
    required this.onToggle,
    required this.onDelete,
  });

  final ChecklistItem item;
  final AqPalette palette;
  final ValueChanged<bool> onToggle;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AqSpace.base, vertical: 4),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AqRadius.card),
        border: Border.all(color: palette.border),
      ),
      child: Row(
        children: <Widget>[
          Checkbox(
            value: item.isDone,
            onChanged: (value) => onToggle(value ?? false),
          ),
          Expanded(
            child: Text(
              item.title,
              style: TextStyle(
                fontSize: 14,
                decoration: item.isDone ? TextDecoration.lineThrough : null,
                color: item.isDone ? palette.dimText : palette.primaryText,
              ),
            ),
          ),
          IconButton(
            icon: Icon(Icons.delete_outline, size: 20, color: palette.secondaryText),
            onPressed: onDelete,
          ),
        ],
      ),
    );
  }
}

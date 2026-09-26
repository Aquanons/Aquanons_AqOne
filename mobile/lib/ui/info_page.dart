import 'package:flutter/material.dart';

import '../core/tokens.dart';

class InfoPage extends StatelessWidget {
  const InfoPage({super.key, required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    return Scaffold(
      backgroundColor: palette.canvas,
      appBar: AppBar(
        title: Text(
          title,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: palette.primaryText,
          ),
        ),
        backgroundColor: palette.surface,
        elevation: 0,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: palette.active,
            size: 20,
          ),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Text(
            body,
            style: TextStyle(
              fontSize: 14,
              color: palette.secondaryText,
              height: 1.55,
            ),
          ),
        ),
      ),
    );
  }
}

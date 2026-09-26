import 'dart:io';

import 'package:flutter/material.dart';

import '../core/tokens.dart';
import '../l10n/app_localizations.dart';
import '../services/backend_client.dart';

const Color _brandPrimary = Color(0xFF0F69C9);
const Color _successGreen = Color(0xFF16A34A);
const Color _dangerRed = Color(0xFFDC2626);

class EnrolmentPage extends StatefulWidget {
  const EnrolmentPage({
    super.key,
    required this.backendClient,
    required this.vesselId,
    this.deviceLabel = 'Fisher handset',
  });

  final BackendClient backendClient;
  final String vesselId;
  final String deviceLabel;

  @override
  State<EnrolmentPage> createState() => _EnrolmentPageState();
}

class _EnrolmentPageState extends State<EnrolmentPage> {
  final TextEditingController _codeController = TextEditingController();
  bool _loading = false;
  String? _statusMessage;
  bool _isSuccess = false;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final code = _codeController.text.trim();
    if (code.isEmpty || _loading) return;

    final t = AppLocalizations.of(context);
    setState(() {
      _loading = true;
      _statusMessage = null;
      _isSuccess = false;
    });

    try {
      final credential = await widget.backendClient.enrollVesselDevice(
        vesselId: widget.vesselId,
        pairingCode: code,
        deviceLabel: widget.deviceLabel,
      );
      if (!mounted) return;
      if (credential != null) {
        setState(() {
          _loading = false;
          _isSuccess = true;
          _statusMessage = t.enrolVerified;
        });
      } else {
        setState(() {
          _loading = false;
          _isSuccess = false;
          _statusMessage = t.enrolCodeInvalid;
        });
      }
    } on VesselAuthException {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _isSuccess = false;
        _statusMessage = t.enrolCodeInvalid;
      });
    } on SocketException {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _isSuccess = false;
        _statusMessage = t.enrolNeedsInternet;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _isSuccess = false;
        _statusMessage = t.enrolNeedsInternet;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: palette.canvas,
      appBar: AppBar(
        backgroundColor: palette.surface,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(
          t.enrolTitle,
          style: TextStyle(
            color: palette.primaryText,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(AqSpace.screen),
        children: <Widget>[
          const SizedBox(height: AqSpace.md),
          Text(
            t.enrolTitle,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: palette.primaryText,
            ),
          ),
          const SizedBox(height: AqSpace.sm),
          Text(
            t.enrolInstructions,
            style: TextStyle(
              fontSize: 14,
              color: palette.secondaryText,
            ),
          ),
          const SizedBox(height: AqSpace.xl),
          TextField(
            controller: _codeController,
            textCapitalization: TextCapitalization.characters,
            autocorrect: false,
            decoration: InputDecoration(
              labelText: t.enrolCodeLabel,
              hintText: t.enrolCodeHint('K7Q4M9PX'),
              filled: true,
              fillColor: palette.surface,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AqRadius.card),
                borderSide: BorderSide(color: palette.border),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AqRadius.card),
                borderSide: BorderSide(color: palette.border),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AqRadius.card),
                borderSide: const BorderSide(color: _brandPrimary, width: 2),
              ),
            ),
          ),
          const SizedBox(height: AqSpace.lg),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              onPressed: _loading ? null : _submit,
              style: ElevatedButton.styleFrom(
                backgroundColor: _brandPrimary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AqRadius.button),
                ),
              ),
              child: _loading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Text(
                      t.enrolVerifyButton,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
            ),
          ),
          if (_statusMessage != null) ...<Widget>[
            const SizedBox(height: AqSpace.lg),
            Container(
              padding: const EdgeInsets.all(AqSpace.md),
              decoration: BoxDecoration(
                color: _isSuccess
                    ? _successGreen.withValues(alpha: 0.1)
                    : _dangerRed.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AqRadius.card),
                border: Border.all(
                  color: _isSuccess ? _successGreen : _dangerRed,
                ),
              ),
              child: Row(
                children: <Widget>[
                  Icon(
                    _isSuccess
                        ? Icons.check_circle_rounded
                        : Icons.error_outline_rounded,
                    color: _isSuccess ? _successGreen : _dangerRed,
                  ),
                  const SizedBox(width: AqSpace.sm),
                  Expanded(
                    child: Text(
                      _statusMessage!,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: _isSuccess ? _successGreen : _dangerRed,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

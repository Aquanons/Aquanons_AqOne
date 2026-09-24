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

class InfoCopy {
  const InfoCopy._();

  static const String about =
      'AqOne\n'
      'Gabay sa Bawat Alon, Konektado sa Bawat Layon\n\n'
      'Fishermen in New Washington, Aklan lose mobile signal as soon as they '
      'reach the fishing ground. When something goes wrong out there, there is '
      'no way to call for help, and the MDRRMO usually hears about it hours '
      'later by word of mouth.\n\n'
      'AqOne carries a distress message over a radio mesh instead of the '
      'cellular network. Your phone hands the SOS to the nearest anchored '
      'buoy over its WiFi. Buoys pass it along by LoRa radio until one of them '
      'reaches shore and forwards it to the MDRRMO dashboard.\n\n'
      'Your phone never needs a signal.';

  static const String help =
      'Sending an SOS\n\n'
      '1. Connect your phone to the WiFi of the nearest AqOne buoy. The '
      'network name starts with "AqOne-".\n'
      '2. Open this app and press the red SOS button.\n'
      '3. Watch the status on the message. It tells you exactly how far your '
      'SOS has travelled.\n\n'
      'What the four statuses mean\n\n'
      'Saved — the SOS is on your phone only. No buoy is in range yet. The app '
      'keeps trying on its own.\n\n'
      'Relayed — a buoy has taken your SOS and is passing it along the radio '
      'mesh. This is as much as your phone can know without a signal.\n\n'
      'Delivered — the MDRRMO dashboard has received it.\n\n'
      'Acknowledged — a responder has seen it and is acting on it.\n\n'
      'The app will never show a later status than the one it has actually '
      'observed. If your message is stuck at Relayed, it is genuinely still '
      'waiting on the mesh.\n\n'
      'If no buoy is in range\n\n'
      'Your SOS is not lost. It stays on your phone and is sent automatically '
      'as soon as a buoy is reachable, even if you close the app.';

  static const String privacy =
      'What AqOne collects\n\n'
      'This app does not ask for an account, a password, an email address, or '
      'a phone number. There is no user database.\n\n'
      'When you first open the app it creates a random identifier on your '
      'device and stores it locally. That identifier, together with the boat '
      'name you enter, is what a responder sees next to your distress call.\n\n'
      'When you send an SOS, the app transmits:\n\n'
      '• your boat name\n'
      '• your GPS position, if your phone has a fix at that moment\n'
      '• the short note you typed, if you typed one\n'
      '• the time you pressed the button\n\n'
      'Precise position is only sent as part of an SOS you deliberately send. The app '
      'does not track or transmit your location in the background, and it does '
      'not record where you fish.\n\n'
      'Weather forecasts and maps\n\n'
      'Weather forecasts use your approximate location (about 11 km) to retrieve '
      'conditions for your general area without disclosing your exact coordinates. '
      'When viewing the online map, the app fetches map tiles for the area you are '
      'viewing directly from OpenStreetMap.\n\n'
      'How it travels\n\n'
      'An SOS is relayed by radio between buoys. Messages are signed so a '
      'responder can tell a real buoy from a fake one, but the content itself '
      'is not encrypted end to end in this version. Treat an SOS as a public '
      'radio call, because that is what it is.\n\n'
      'Deleting your data\n\n'
      'Uninstalling the app removes the identifier and every message stored on '
      'your phone. Distress calls already delivered to the MDRRMO remain part '
      'of their incident record.';

  static const String terms =
      'Please read this before relying on AqOne.\n\n'
      'AqOne is a prototype\n\n'
      'This software was built for a hackathon and has not been certified, '
      'independently tested, or approved as marine safety equipment.\n\n'
      'It is not a replacement for safety gear\n\n'
      'Do not go to sea relying on this app alone. Carry the flotation, '
      'signalling and communication equipment you would normally carry. AqOne '
      'is an addition to those, never a substitute.\n\n'
      'Delivery is not guaranteed\n\n'
      'An SOS travels by radio between buoys. Radio is affected by weather, '
      'distance, obstructions, buoy battery level, and interference. A message '
      'may be delayed or may not arrive at all. The app shows you honestly how '
      'far your message has reached, and never claims more than it knows.\n\n'
      'Coverage is limited\n\n'
      'AqOne only works within radio range of a deployed buoy. Outside that '
      'range your SOS stays saved on your phone until you come back into '
      'range.\n\n'
      'Responsible use\n\n'
      'Send an SOS only in a genuine emergency. False alarms waste rescue '
      'resources and put responders at risk.';
}

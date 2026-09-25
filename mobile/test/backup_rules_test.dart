import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('AndroidManifest.xml enables backup pointing to custom rules', () {
    final manifestFile = File('android/app/src/main/AndroidManifest.xml');
    expect(manifestFile.existsSync(), isTrue);
    final manifest = manifestFile.readAsStringSync();

    expect(manifest, contains('android:allowBackup="true"'));
    expect(manifest, contains('android:fullBackupContent="@xml/backup_rules"'));
    expect(manifest, contains('android:dataExtractionRules="@xml/data_extraction_rules"'));
  });

  test('backup rules XML files include only aqone_identity_backup shared-prefs', () {
    final backupRulesFile = File('android/app/src/main/res/xml/backup_rules.xml');
    final dataExtractionRulesFile = File('android/app/src/main/res/xml/data_extraction_rules.xml');

    expect(backupRulesFile.existsSync(), isTrue, reason: 'backup_rules.xml must exist');
    expect(dataExtractionRulesFile.existsSync(), isTrue, reason: 'data_extraction_rules.xml must exist');

    final backupContent = backupRulesFile.readAsStringSync();
    final extractionContent = dataExtractionRulesFile.readAsStringSync();

    // Parse all <include ... /> tags
    final includeRegex = RegExp(r'<include\s+([^>]+)/>');

    final backupIncludes = includeRegex.allMatches(backupContent).toList();
    expect(backupIncludes, isNotEmpty);
    for (final m in backupIncludes) {
      final attrs = m.group(1)!;
      expect(attrs, contains('domain="sharedpref"'));
      expect(attrs, contains('aqone_identity_backup'));
    }

    final extractionIncludes = includeRegex.allMatches(extractionContent).toList();
    expect(extractionIncludes, isNotEmpty);
    for (final m in extractionIncludes) {
      final attrs = m.group(1)!;
      expect(attrs, contains('domain="sharedpref"'));
      expect(attrs, contains('aqone_identity_backup'));
    }
  });
}

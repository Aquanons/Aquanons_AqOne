import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Release signing credentials, read from android/key.properties.
//
// That file is gitignored and must never be committed: it holds the keystore
// password. See docs/25_MOBILE_SECURITY_IMPLEMENTATION_PLAN.md Phase 6 and
// android/key.properties.example for how to create it.
//
// Absent on a teammate's machine, or in CI without the secret, this stays
// empty and release builds fail fast with instructions pointing to
// mobile/README.md. Teammates without the key use 'flutter build apk --debug'.
val keystoreProperties = Properties().apply {
    val file = rootProject.file("key.properties")
    if (file.exists()) {
        file.inputStream().use { load(it) }
    }
}
val hasReleaseKeystore = keystoreProperties.getProperty("storeFile") != null

android {
    namespace = "ph.aqone.app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // flutter_local_notifications 10+ requires core-library desugaring for
        // its scheduling support, and applies it even when an app only ever
        // shows notifications immediately (rename eta_notifier.dart). Needed
        // on every Android build, not just release's R8 pass.
        isCoreLibraryDesugaringEnabled = true
    }

    signingConfigs {
        if (hasReleaseKeystore) {
            create("release") {
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    defaultConfig {
        // ph.aqone.app, not Flutter's com.example placeholder: Play rejects
        // com.example.*, and this id is already what the app sends as its
        // OSM tile User-Agent, so the two now agree.
        //
        // Changing this again later moves the app's private data directory,
        // which would orphan the local database - including any queued SOS.
        applicationId = "ph.aqone.app"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        // Desugaring bundles code that pushes a minSdk-era APK over the
        // dalvik method reference cap.
        multiDexEnabled = true
    }

    buildTypes {
        release {
            // Real key when key.properties is present. No debug fallback: a debug-signed
            // APK must never be distributed (SEC-32). Teammates without key.properties
            // must use 'flutter build apk --debug'.
            if (hasReleaseKeystore) {
                signingConfig = signingConfigs.getByName("release")
            }

            // Shrink and obfuscate. Off by default in Flutter's template; on
            // here because an unobfuscated release ships readable class and
            // method names, which hands an attacker a map of the SOS and
            // credential paths for free.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
}

gradle.taskGraph.whenReady {
    val isReleaseBuild = allTasks.any { task ->
        val name = task.name.lowercase()
        (name.contains("release") && (name.startsWith("assemble") || name.startsWith("bundle") || name.startsWith("package")))
    }
    if (isReleaseBuild && !hasReleaseKeystore) {
        throw GradleException(
            "Release builds require android/key.properties with valid release keystore credentials. " +
            "Teammates without the release key must build with 'flutter build apk --debug'. " +
            "See mobile/README.md for keystore instructions."
        )
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}

flutter {
    source = "../.."
}

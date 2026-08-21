plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.kybirdlabs.sugarscan"
    // flutter.compileSdkVersion 은 아직 36 인데 flutter_secure_storage 와
    // permission_handler_android 가 37 을 요구한다. 37 은 SDK 저장소에
    // `android-37.0` 이라는 부(minor) 버전 이름으로만 존재하고, 이를 해석하려면
    // AGP 9.1.1 이상이 필요하다(settings.gradle.kts 참조).
    compileSdk = 37
    ndkVersion = flutter.ndkVersion

    compileOptions {
        // flutter_local_notifications 가 요구한다. minSdk 아래 기기에서도
        // java.time 같은 최신 표준 라이브러리를 쓸 수 있게 하는 것이다.
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.kybirdlabs.sugarscan"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        // flutter.minSdkVersion(24)이 아니라 26. `health` 플러그인(Health
        // Connect 연동)이 요구한다. Android 8.0 미만 기기를 포기하는 결정이다.
        minSdk = 26
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
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

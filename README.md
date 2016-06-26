# Dashchan Extensions

This repository is designed to store Dashchan extensions source code.

The source code is available in specific branch for every extension.

Use `git clone -b %CHAN_NAME% https://github.com/Mishiranu/DashchanExtensions` to clone specific branch.

# Building Guide

1. Install JDK 7 or higher
2. Install Android SDK, define `ANDROID_HOME` environment variable or set `sdk.dir` in `local.properties`
3. Install Android NDK, define `ANDROID_NDK_HOME` environment variable or set `ndk.dir` in `local.properties`
4. Install Gradle
5. Run `gradle assembleRelease`

The resulting APK file will appear in `build/outputs/apk` directory.

The API library may be updated. Use `gradle --refresh-dependencies assembleRelease` to build, then.

### Build Signed Binary

You can create `keystore.properties` in the source code directory with the following properties:

```properties
debug.storeFile=%PATH_TO_KEYSTORE_FILE%
debug.storePassword=%KEYSTORE_PASSWORD%
debug.keyAlias=%KEY_ALIAS%
debug.keyPassword=%KEY_PASSWORD%

release.storeFile=%PATH_TO_KEYSTORE_FILE%
release.storePassword=%KEYSTORE_PASSWORD%
release.keyAlias=%KEY_ALIAS%
release.keyPassword=%KEY_PASSWORD%
```
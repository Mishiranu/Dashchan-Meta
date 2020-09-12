# Dashchan Extensions

This repository is designed to store Dashchan extensions source code and themes.

The source code is available in specific branch for every extension.

Use `git clone -b %CHAN_NAME% https://github.com/Mishiranu/Dashchan-Extensions` to clone specific branch.

Video player libraries extension is located in the [neighboring repository](https://github.com/Mishiranu/Dashchan-Webm).

General dependencies: [Public API](https://github.com/Mishiranu/Dashchan-Library),
[Static Library](https://github.com/Mishiranu/Dashchan-Static).

## Building Guide

1. Install JDK 8 or higher
2. Install Android SDK, define `ANDROID_HOME` environment variable or set `sdk.dir` in `local.properties`
3. Install Gradle
4. Run `gradle assembleRelease`

The resulting APK file will appear in `build/outputs/apk` directory.

The API library may be updated. Use `gradle --refresh-dependencies assembleRelease` to build, then.

### Build Signed Binary

You can create `keystore.properties` in the source code directory with the following properties:

```properties
store.file=%PATH_TO_KEYSTORE_FILE%
store.password=%KEYSTORE_PASSWORD%
key.alias=%KEY_ALIAS%
key.password=%KEY_PASSWORD%
```

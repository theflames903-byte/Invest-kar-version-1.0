[app]
title = Invest Kar
package.name = investkar
package.domain = com.investkar.app
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json
version = 1.0
requirements = python3,kivy,sqlite3,requests,openssl

# Android specific
android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
android.sdk = 24
android.ndk = 25b
android.gradle_dependencies = implementation 'androidx.core:core:1.9.0'

# Icon
icon.filename = assets/icon.png

[buildozer]
log_level = 2
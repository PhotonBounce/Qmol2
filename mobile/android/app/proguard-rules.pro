# Q-Mol ProGuard Rules

# Flutter
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }
-keep class com.google.android.gms.** { *; }
-keep class androidx.** { *; }
-keep class com.google.firebase.** { *; }
-dontwarn io.flutter.embedding.**

# JSON serialization (freezed + json_serializable)
-keep class qmol.models.** { *; }
-keepclassmembers class qmol.models.** { *; }

# Dio / HTTP
-dontwarn com.stericson.RootShell.**
-keepclassmembers class * extends com.stericson.RootShell.execution.Command {
    <init>(...);
}

# Secure Storage
-keep class com.it_nomads.fluttersecurestorage.** { *; }

# In-app purchase
-keep class com.android.billingclient.** { *; }
-keep class com.android.vending.billing.** { *; }
-keep class com.revenuecat.purchases.** { *; }

# URL Launcher
-keep class io.flutter.plugins.urllauncher.** { *; }

# Share Plus
-keep class io.flutter.plugins.share.** { *; }

# Local Notifications
-keep class com.dexterous.flutterlocalnotifications.** { *; }

# Permission Handler
-keep class com.baseflow.permissionhandler.** { *; }

# Image Picker
-keep class io.flutter.plugins.imagepicker.** { *; }

# File Picker
-keep class com.mr.flutter.plugin.filepicker.** { *; }

# Path Provider
-keep class io.flutter.plugins.pathprovider.** { *; }

# Package Info Plus
-keep class dev.fluttercommunity.plus.packageinfo.** { *; }

# Device Info Plus
-keep class dev.fluttercommunity.plus.device_info.** { *; }

# Connectivity Plus
-keep class dev.fluttercommunity.plus.connectivity.** { *; }

# General
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes Exceptions
-keepattributes InnerClasses
-keepattributes EnclosingMethod
-keepattributes LineNumberTable
-keepattributes SourceFile
-keepattributes Deprecated

# Prevent R8 from stripping enum values
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

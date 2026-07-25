@file:Suppress("UnstableApiUsage")

rootProject.name = "AI-Chat-Advanced"
enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")

pluginManagement {
    includeBuild("build-convention-plugins")
    repositories {
        google {
            mavenContent {
                includeGroupAndSubgroups("androidx")
                includeGroupAndSubgroups("com.android")
                includeGroupAndSubgroups("com.google")
                includeGroupAndSubgroups("org.chromium.net")
                includeGroupAndSubgroups("com.crashlytics.sdk")
            }
        }
        mavenCentral()
        gradlePluginPortal()
        maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
    }
}

dependencyResolutionManagement {
    repositories {
        google {
            mavenContent {
                includeGroupAndSubgroups("androidx")
                includeGroupAndSubgroups("com.android")
                includeGroupAndSubgroups("com.google")
                includeGroupAndSubgroups("org.chromium.net")
                includeGroupAndSubgroups("com.crashlytics.sdk")
            }
        }
        mavenCentral()
        maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
    }
}

include(":androidApp")
include(":composeApp")
include(":core:viewmodel")
include(":feature:ai")
include(":feature:voice")
include(":feature:chat")
include(":feature:settings")

package com.alva

import com.alva.utils.libs

plugins {
    kotlin("multiplatform")
    id("com.android.kotlin.multiplatform.library")
}

val iosMinDeploymentTarget: String = libs.versions.iosMinDeploymentTarget.get()

kotlin {
    jvmToolchain(21)

    android {
        compileSdk = libs.versions.compileSdk.get().toInt()
        minSdk = 30
        androidResources {
            enable = true
        }
    }

    listOf(
        iosArm64(),
        iosSimulatorArm64()
    ).forEach { target ->
        target.compilations.configureEach {
            compileTaskProvider.configure {
                compilerOptions {
                    freeCompilerArgs.add(
                        "-Xoverride-konan-properties=osVersionMin.${target.konanTarget.name}=$iosMinDeploymentTarget"
                    )
                }
            }
        }
    }
}

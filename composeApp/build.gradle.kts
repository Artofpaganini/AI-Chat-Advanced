plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
}

kotlin {
    android {
        namespace = "com.jarvis.chat"
    }

    listOf(
        iosArm64(),
        iosSimulatorArm64(),
    ).forEach { target ->
        target.binaries.framework {
            baseName = "JarvisApp"
            isStatic = true
        }
    }

    sourceSets {
        commonMain.dependencies {
            implementation(projects.feature.chat)
            implementation(libs.compose.material3)
            implementation(libs.koin.core)
        }
    }
}

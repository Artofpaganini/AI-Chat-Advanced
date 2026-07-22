@file:Suppress("UnstableApiUsage")

package com.alva.utils

import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.dsl.CommonExtension
import com.android.build.api.dsl.LibraryExtension
import com.android.build.api.dsl.TestExtension
import com.android.build.api.variant.KotlinMultiplatformAndroidComponentsExtension
import com.android.build.api.variant.LibraryAndroidComponentsExtension
import org.gradle.accessors.dm.LibrariesForLibs
import org.gradle.api.Project
import org.gradle.api.plugins.PluginContainer
import org.gradle.kotlin.dsl.findByType
import org.gradle.kotlin.dsl.the
import org.gradle.kotlin.dsl.withType
import org.jetbrains.compose.ComposeExtension
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmCompilerOptions
import org.jetbrains.kotlin.gradle.dsl.KotlinMultiplatformExtension
import org.jetbrains.kotlin.gradle.tasks.KotlinJvmCompile

private val Project.androidExtension: CommonExtension
    get() {
        return extensions.findByType(ApplicationExtension::class)
            ?: extensions.findByType(LibraryExtension::class)
            ?: extensions.findByType(TestExtension::class)
            ?: error(
                "\"Project.androidExtension\" value may be called only "
                        + "from android application"
                        + " or android library gradle script",
            )
    }

internal fun PluginContainer.applyIfNeeded(
    id: String,
    vararg ids: String,
): Boolean {
    if (hasPlugin(id) || ids.any(::hasPlugin)) return false

    apply(id)
    return true
}

internal fun Project.androidConfig(
    block: CommonExtension.() -> Unit
): Unit = block(androidExtension)

internal fun Project.kotlinJvmCompilerOptions(block: KotlinJvmCompilerOptions.() -> Unit) {
    tasks.withType<KotlinJvmCompile>().configureEach {
        compilerOptions(block)
    }
}

internal val Project.libs: LibrariesForLibs
    get() = the<LibrariesForLibs>()

private val Project.kmpExtension: KotlinMultiplatformExtension
    get() {
        return extensions.findByType(KotlinMultiplatformExtension::class) ?: error(
            "\"Project.kmpExtension\" value may be called only "
                    + "from kotlin multiplatform gradle script",
        )
    }

internal inline fun Project.kmpConfig(
    block: KotlinMultiplatformExtension.() -> Unit
) = kmpExtension.block()

private val Project.kmpAndroidLibComponentExtension: KotlinMultiplatformAndroidComponentsExtension
    get() {
        return extensions.findByType(KotlinMultiplatformAndroidComponentsExtension::class) ?: error(
            "\"Project.kmpAndroidLibComponentExtension\" value may be called only "
                    + "from kotlin multiplatform android gradle script",
        )
    }

internal inline fun Project.kmpAndroidLibComponentConfig(
    block: KotlinMultiplatformAndroidComponentsExtension.() -> Unit
) = kmpAndroidLibComponentExtension.block()

private val Project.androidLibComponentExtension: LibraryAndroidComponentsExtension
    get() {
        return extensions.findByType(LibraryAndroidComponentsExtension::class) ?: error(
            "\"Project.androidLibComponentExtension\" value may be called only "
                    + "from android library gradle script",
        )
    }

internal inline fun Project.androidLibComponentConfig(
    block: LibraryAndroidComponentsExtension.() -> Unit
) = androidLibComponentExtension.block()

internal val Project.composeExt: ComposeExtension
    get() = extensions.findByType(ComposeExtension::class.java)
        ?: error("Compose plugin is not applied")

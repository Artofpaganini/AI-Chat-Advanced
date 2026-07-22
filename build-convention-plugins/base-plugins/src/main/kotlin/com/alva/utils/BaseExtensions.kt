@file:Suppress("ktlint")

package com.alva.utils

import io.gitlab.arturbosch.detekt.extensions.DetektExtension
import org.gradle.api.Project
import org.gradle.kotlin.dsl.findByType

internal val Project.detektExtension: DetektExtension
    get() = checkNotNull(extensions.findByType(DetektExtension::class))

internal fun Project.detektConfig(block: DetektExtension.() -> Unit) = block(detektExtension)

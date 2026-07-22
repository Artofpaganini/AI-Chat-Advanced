package com.alva

import com.alva.utils.applyIfNeeded
import com.alva.utils.detektConfig
import com.alva.utils.libs
import com.alva.utils.sourceExcludeGlobs
import io.gitlab.arturbosch.detekt.Detekt


plugins.applyIfNeeded(libs.plugins.detekt.get().pluginId)

detektConfig {
    // Version of detekt that will be used. When unspecified the latest detekt
    // version found will be used. Override to stay on the same version.
    // Note: Using hardcoded version due to version catalog access issues in precompiled script plugins
    toolVersion = "1.23.8"

    // The directories where detekt looks for source files.
    // Defaults to `files("src/main/java", "src/test/java", "src/main/kotlin", "src/test/kotlin")`.
    //    source.setFrom()

    // Define the detekt configuration(s) you want to use.
    // Defaults to the default detekt configuration.
    config.setFrom(
        File(rootProject.rootDir, "config/detekt/detekt.yml"),
        File(rootProject.rootDir, "config/detekt/detekt-compose.yml"),
    )

    // Applies the config files on top of detekt's default config file. `false` by default.
    buildUponDefaultConfig = false

    // Turns on all the rules. `false` by default.
    allRules = false

    // Specifying a baseline file. All findings stored in this file in subsequent runs of detekt.
    baseline = file("detekt-baseline.xml")

    // Disables all default detekt rulesets and will only run detekt with custom rules
    // defined in plugins passed in with `detektPlugins` configuration. `false` by default.
    disableDefaultRuleSets = false

    // Adds devug output during task execution. `false` by default.
    debug = false

    // If set to `true` the build does not fail when the
    // maxIssues count was reached. Defaults to `false`.
    ignoreFailures = false

    parallel = true
}

val isolatedImportTasks = setOf("detektFixImports", "detektCheckImports")

tasks.withType<Detekt>().configureEach {
    if (name in isolatedImportTasks) {
        return@configureEach
    }
    val changedFilesProperty = project.findProperty("changedFiles") as? String
    if (changedFilesProperty != null) {
        // Режим pre-push: проверяем только изменённые файлы
        val changedFilesList = changedFilesProperty.split(",")
            .filter { it.endsWith(".kt") }
            .map { File(rootProject.rootDir, it) }
            .filter { it.exists() }
        setSource(project.files(changedFilesList))
    } else {
        // Полная проверка: все файлы проекта
        setSource(projectDir)
        include("**/src/*/kotlin/**/*.kt")
    }

    sourceExcludeGlobs.forEach { excludeGlob ->
        exclude(excludeGlob)
    }

    with(this.project) {
        reports {
            xml.apply {
                isEnabled = true
                outputLocation.set(layout.buildDirectory.file("reports/detekt/detekt.xml"))
            }

            txt.apply {
                isEnabled = true
                outputLocation.set(layout.buildDirectory.file("reports/detekt/detekt.txt"))
            }

            html.apply {
                isEnabled = true
                outputLocation.set(layout.buildDirectory.file("reports/detekt/detekt.html"))
            }

            sarif.apply {
                isEnabled = false
                outputLocation.set(layout.buildDirectory.file("reports/detekt/detekt.sarif"))
            }

            md.apply {
                // Required to fail Gradle task
                isEnabled = true
                outputLocation.set(layout.buildDirectory.file("reports/detekt/detekt.md"))
            }
        }
    }
}

dependencies.add("detektPlugins", libs.classpath.detekt.compose)
dependencies.add("detektPlugins", libs.classpath.detekt.formatting)

fun org.gradle.api.tasks.SourceTask.applyChangedFilesSource() {
    val changedFilesProperty = project.findProperty("changedFiles") as? String
    if (changedFilesProperty != null) {
        val changedFilesList = changedFilesProperty.split(",")
            .filter { it.endsWith(".kt") }
            .map { File(rootProject.rootDir, it) }
            .filter { it.exists() }
        setSource(project.files(changedFilesList))
    } else {
        setSource(projectDir)
        include("**/src/*/kotlin/**/*.kt")
    }

    sourceExcludeGlobs.forEach { excludeGlob ->
        exclude(excludeGlob)
    }
}

// Commit-time автофикс: убирает unused imports в staged-файлах.
// Использует изолированный config detekt-imports.yml (только formatting>UnusedImports),
// поэтому не падает и ничего лишнего не правит.
tasks.register<Detekt>("detektFixImports") {
    applyChangedFilesSource()
    config.setFrom(File(rootProject.rootDir, "config/detekt/detekt-imports.yml"))
    buildUponDefaultConfig = false
    autoCorrect = true
    ignoreFailures = true
    // Автофикс правит файлы in-place — Gradle не отслеживает это как output,
    // поэтому отключаем UP-TO-DATE, иначе задача закешируется и не применит фикс повторно.
    outputs.upToDateWhen { false }
    reports {
        xml.required.set(false)
        html.required.set(false)
        txt.required.set(false)
        sarif.required.set(false)
        md.required.set(false)
    }
}

// Commit-time check: тот же изолированный config, но без автофикса.
// Падает, если в staged-файлах остались unused imports (например partially-staged).
tasks.register<Detekt>("detektCheckImports") {
    applyChangedFilesSource()
    config.setFrom(File(rootProject.rootDir, "config/detekt/detekt-imports.yml"))
    buildUponDefaultConfig = false
    autoCorrect = false
    ignoreFailures = false
    reports {
        xml.required.set(false)
        txt.required.set(false)
        html.required.set(false)
        sarif.required.set(false)
        md.required.set(false)
    }
}

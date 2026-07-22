package com.alva.scaffold.tasks

import com.alva.scaffold.ScaffoldEngine
import org.gradle.api.DefaultTask
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.provider.Property
import org.gradle.api.tasks.Internal

// Базовый таск скаффолдинга: общие флаги force/dry-run и запуск движка.
abstract class ScaffoldTask : DefaultTask() {

    @get:Internal
    abstract val force: Property<Boolean>

    @get:Internal
    abstract val dryRun: Property<Boolean>

    // Корень проекта захватывается на configuration-фазе (плагин задаёт его при регистрации),
    // чтобы не трогать Task.project в @TaskAction — это запрещено с configuration cache.
    @get:Internal
    abstract val rootDirectory: DirectoryProperty

    protected fun engine(): ScaffoldEngine =
        ScaffoldEngine(
            rootDir = rootDirectory.get().asFile,
            force = force.getOrElse(false),
            dryRun = dryRun.getOrElse(false),
        )

    protected fun emit(engine: ScaffoldEngine) {
        logger.lifecycle(engine.report)
    }

    protected fun requireName(value: String?, hint: String): String {
        if (value.isNullOrBlank()) {
            error(hint)
        }
        return value
    }
}

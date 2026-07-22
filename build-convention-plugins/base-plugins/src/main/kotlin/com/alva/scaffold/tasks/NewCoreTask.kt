package com.alva.scaffold.tasks

import org.gradle.api.provider.Property
import org.gradle.api.tasks.Internal
import org.gradle.api.tasks.TaskAction
import org.gradle.api.tasks.options.Option

// core --name=analytics [--ui]
abstract class NewCoreTask : ScaffoldTask() {

    @get:Internal
    @get:Option(option = "name", description = "Имя core-модуля (snake_case, обязательное)")
    abstract val moduleName: Property<String>

    @get:Internal
    @get:Option(option = "ui", description = "Добавить cmp.setup + material3 (как core/uikit)")
    abstract val ui: Property<Boolean>

    @get:Internal
    @get:Option(option = "force", description = "Перезаписать существующие файлы")
    abstract override val force: Property<Boolean>

    @get:Internal
    @get:Option(option = "preview", description = "Показать дифф авто-вайринга, ничего не писать (dry-run)")
    abstract override val dryRun: Property<Boolean>

    @TaskAction
    fun generateCore() {
        val coreName = requireName(moduleName.orNull, "core: укажи --name=<snake_case> (пример: --name=analytics)")
        val engine = engine()
        engine.core(name = coreName, withUi = ui.getOrElse(false))
        emit(engine)
    }
}

package com.alva.scaffold.tasks

import org.gradle.api.provider.Property
import org.gradle.api.tasks.Internal
import org.gradle.api.tasks.options.Option

// База для сабкоманд, добавляющих классы в существующую feature
// (viewmodel/usecase/repository/screen/component/model).
abstract class FeatureScopedTask : ScaffoldTask() {

    @get:Internal
    @get:Option(option = "name", description = "Имя класса (PascalCase, обязательное)")
    abstract val className: Property<String>

    @get:Internal
    @get:Option(option = "feature", description = "Имя feature-модуля (snake_case, обязательное)")
    abstract val feature: Property<String>

    @get:Internal
    @get:Option(option = "force", description = "Перезаписать существующие файлы")
    abstract override val force: Property<Boolean>

    @get:Internal
    @get:Option(option = "preview", description = "Показать дифф авто-вайринга, ничего не писать (dry-run)")
    abstract override val dryRun: Property<Boolean>

    protected fun resolvePascalAndFeature(commandHint: String): Pair<String, String> {
        val pascal = requireName(className.orNull, "$commandHint: укажи --name=<PascalCase>")
        val featureName = requireName(feature.orNull, "$commandHint: укажи --feature=<snake_case>")
        return pascal to featureName
    }
}

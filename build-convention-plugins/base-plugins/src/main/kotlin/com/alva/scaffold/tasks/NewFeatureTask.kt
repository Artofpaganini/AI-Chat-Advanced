package com.alva.scaffold.tasks

import com.alva.scaffold.LayerResolver
import org.gradle.api.provider.Property
import org.gradle.api.tasks.Internal
import org.gradle.api.tasks.TaskAction
import org.gradle.api.tasks.options.Option

// feature --name=sleep --full | --layers=domain,data | --no-data | --with-viewmodel
abstract class NewFeatureTask : ScaffoldTask() {

    @get:Internal
    @get:Option(option = "name", description = "Имя feature-модуля (snake_case, обязательное)")
    abstract val moduleName: Property<String>

    @get:Internal
    @get:Option(option = "full", description = "Все слои: nav+presentation+domain+data")
    abstract val full: Property<Boolean>

    @get:Internal
    @get:Option(option = "layers", description = "Явный CSV-список слоёв: nav,presentation,domain,data")
    abstract val layers: Property<String>

    @get:Internal
    @get:Option(option = "no-presentation", description = "Исключить слой presentation (база --full)")
    abstract val noPresentation: Property<Boolean>

    @get:Internal
    @get:Option(option = "no-domain", description = "Исключить слой domain (база --full)")
    abstract val noDomain: Property<Boolean>

    @get:Internal
    @get:Option(option = "no-data", description = "Исключить слой data (база --full)")
    abstract val noData: Property<Boolean>

    @get:Internal
    @get:Option(option = "no-nav", description = "Исключить слой nav (база --full)")
    abstract val noNav: Property<Boolean>

    @get:Internal
    @get:Option(option = "with-viewmodel", description = "Тонкий модуль + UDF: слои nav+presentation")
    abstract val withViewModel: Property<Boolean>

    @get:Internal
    @get:Option(option = "force", description = "Перезаписать существующие файлы")
    abstract override val force: Property<Boolean>

    @get:Internal
    @get:Option(option = "preview", description = "Показать дифф авто-вайринга, ничего не писать (dry-run)")
    abstract override val dryRun: Property<Boolean>

    @TaskAction
    fun generateFeature() {
        val featureName = requireName(moduleName.orNull, "feature: укажи --name=<snake_case> (пример: --name=sleep_timer)")
        val noLayers = buildSet {
            if (noNav.getOrElse(false)) add("nav")
            if (noPresentation.getOrElse(false)) add("presentation")
            if (noDomain.getOrElse(false)) add("domain")
            if (noData.getOrElse(false)) add("data")
        }
        val resolved = LayerResolver.resolve(
            full = full.getOrElse(false),
            withViewModel = withViewModel.getOrElse(false),
            layersCsv = layers.getOrElse(""),
            noLayers = noLayers,
        )
        val engine = engine()
        engine.feature(name = featureName, layers = resolved)
        emit(engine)
    }
}

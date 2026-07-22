package com.alva.scaffold.tasks

import org.gradle.api.provider.Property
import org.gradle.api.tasks.Internal
import org.gradle.api.tasks.TaskAction
import org.gradle.api.tasks.options.Option

// viewModel --name=Sleep --feature=sleep_timer
abstract class NewViewModelTask : FeatureScopedTask() {
    @TaskAction
    fun generateViewModel() {
        val (pascal, featureName) = resolvePascalAndFeature("viewModel")
        val engine = engine()
        engine.viewModel(pascal = pascal, feature = featureName)
        emit(engine)
    }
}

// useCase --name=GetSleep --feature=sleep_timer
abstract class NewUseCaseTask : FeatureScopedTask() {
    @TaskAction
    fun generateUseCase() {
        val (pascal, featureName) = resolvePascalAndFeature("useCase")
        val engine = engine()
        engine.useCase(pascal = pascal, feature = featureName)
        emit(engine)
    }
}

// repository --name=Sleep --feature=sleep_timer
abstract class NewRepositoryTask : FeatureScopedTask() {
    @TaskAction
    fun generateRepository() {
        val (pascal, featureName) = resolvePascalAndFeature("repository")
        val engine = engine()
        engine.repository(pascal = pascal, feature = featureName)
        emit(engine)
    }
}

// screen --name=SleepDetail --feature=sleep_timer
abstract class NewScreenTask : FeatureScopedTask() {
    @TaskAction
    fun generateScreen() {
        val (pascal, featureName) = resolvePascalAndFeature("screen")
        val engine = engine()
        engine.screen(pascal = pascal, feature = featureName)
        emit(engine)
    }
}

// component --name=SleepCard --feature=sleep_timer
abstract class NewComponentTask : FeatureScopedTask() {
    @TaskAction
    fun generateComponent() {
        val (pascal, featureName) = resolvePascalAndFeature("component")
        val engine = engine()
        engine.component(pascal = pascal, feature = featureName)
        emit(engine)
    }
}

// model --name=SleepSession --feature=sleep_timer [--domain-only|--data-only]
abstract class NewModelTask : FeatureScopedTask() {

    @get:Internal
    @get:Option(option = "domain-only", description = "Только domain-модель")
    abstract val domainOnly: Property<Boolean>

    @get:Internal
    @get:Option(option = "data-only", description = "Только data-модель + mapper")
    abstract val dataOnly: Property<Boolean>

    @TaskAction
    fun generateModel() {
        val (pascal, featureName) = resolvePascalAndFeature("model")
        val engine = engine()
        engine.model(
            pascal = pascal,
            feature = featureName,
            domainOnly = domainOnly.getOrElse(false),
            dataOnly = dataOnly.getOrElse(false),
        )
        emit(engine)
    }
}

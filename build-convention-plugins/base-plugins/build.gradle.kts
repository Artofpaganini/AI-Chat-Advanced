plugins {
    `kotlin-dsl`
    `kotlin-dsl-precompiled-script-plugins`
    `java-gradle-plugin`
}

group = "io.github.alva.gradle.build.convension.plugins"


repositories {
    google()
    mavenCentral()
    gradlePluginPortal()
    maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
}

dependencies {
    implementation(libs.classpath.kotlin)
    implementation(libs.classpath.kotlin.serialization)
    implementation(libs.classpath.android)
    implementation(libs.classpath.compose)
    implementation(libs.classpath.compose.compiler)
    implementation(libs.classpath.detekt)

    // Workaround for version catalog working inside precompiled scripts
    // Issue - https://github.com/gradle/gradle/issues/15383
    implementation(files(libs.javaClass.superclass.protectionDomain.codeSource.location))

}

java {
    targetCompatibility = JavaVersion.VERSION_21
    sourceCompatibility = JavaVersion.VERSION_21
}

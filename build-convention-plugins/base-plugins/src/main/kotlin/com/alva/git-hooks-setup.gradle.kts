package com.alva

tasks.register<Copy>("installGitHooks") {
    description = "Copies git hooks from scripts/githooks/ to .git/hooks/"
    group = "git hooks"

    val sourceDir = project.rootProject.layout.projectDirectory.dir("scripts/githooks")
    val targetDir = project.rootProject.layout.projectDirectory.dir(".git/hooks")

    from(sourceDir) {
        include("**/*")
    }
    into(targetDir)
    filePermissions {
        unix("rwxr-xr-x")
    }
    onlyIf {
        sourceDir.asFile.exists() && targetDir.asFile.exists()
    }
}

listOf("preBuild", "build", "assemble").forEach { taskName ->
    tasks.matching { it.name == taskName }.configureEach {
        dependsOn("installGitHooks")
    }
}

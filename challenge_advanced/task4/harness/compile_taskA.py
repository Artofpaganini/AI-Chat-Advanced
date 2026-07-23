"""Компиляция кода, сгенерированного в задаче A. Проверка «оно вообще собирается».

Собираем в клоне проекта: код каждой модели кладём как модуль `feature/translate`,
подключаем в settings.gradle.kts, компилируем, считаем ошибки компилятора.

Запуск: python3 compile_taskA.py <sandbox>
"""

import json
import os
import re
import shutil
import subprocess
import sys

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_ROOT = os.path.join(TASK_ROOT, "artifacts", "generated")
JAVA_HOME = "/Users/Victor/Library/Java/JavaVirtualMachines/corretto-21.0.9/Contents/Home"
BUILD_TASK_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".build_task")

MODULE_BUILD_FILE = """plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
    alias(libs.plugins.kotlinx.serialization)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.feature.translate"
    }

    sourceSets {
        commonMain.dependencies {
            api(projects.feature.ai)
            implementation(projects.core.viewmodel)
            implementation(projects.composeApp)
            implementation(libs.compose.material3)
            implementation(libs.androidx.lifecycle.viewmodel)
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.client.json)
            implementation(libs.koin.core)
            implementation(libs.koin.compose.viewmodel)
        }
    }
}
"""


def gradle(sandbox, arguments, timeout=1800):
    environment = dict(os.environ, JAVA_HOME=JAVA_HOME)
    return subprocess.run(["./gradlew", *arguments, "--console=plain"],
                          cwd=sandbox, capture_output=True, text=True, timeout=timeout, env=environment)


def detect_build_task(sandbox, module=":feature:chat"):
    if os.path.exists(BUILD_TASK_CACHE):
        with open(BUILD_TASK_CACHE, encoding="utf-8") as file:
            return file.read().strip()
    result = gradle(sandbox, [f"{module}:tasks", "--all", "-q", "--offline"])
    candidates = re.findall(r"^(compile\w*Kotlin\w*)", result.stdout, re.MULTILINE)
    preferred = ["compileDebugKotlinAndroid", "compileKotlinAndroid", "compileKotlinMetadata"]
    task = next((name for name in preferred if name in candidates), candidates[0] if candidates else "compileKotlinMetadata")
    with open(BUILD_TASK_CACHE, "w", encoding="utf-8") as file:
        file.write(task)
    return task


def reset(sandbox):
    subprocess.run(["git", "checkout", "--", "."], cwd=sandbox, check=False)
    subprocess.run(["git", "clean", "-fdq", "--", "feature", "settings.gradle.kts"], cwd=sandbox, check=False)


def install(sandbox, model_dir):
    target = os.path.join(sandbox, "feature", "translate")
    shutil.rmtree(target, ignore_errors=True)
    source = os.path.join(model_dir, "feature", "translate")
    if not os.path.isdir(source):
        # модель могла разложить файлы по другому корню - забираем всё, что есть
        source = model_dir
        for root, _, files in os.walk(model_dir):
            if root.endswith(os.path.join("feature", "translate")):
                source = root
                break
    shutil.copytree(source, target, dirs_exist_ok=True)
    with open(os.path.join(target, "build.gradle.kts"), "w", encoding="utf-8") as file:
        file.write(MODULE_BUILD_FILE)
    settings = os.path.join(sandbox, "settings.gradle.kts")
    with open(settings, encoding="utf-8") as file:
        content = file.read()
    if ":feature:translate" not in content:
        content += '\ninclude(":feature:translate")\n'
        with open(settings, "w", encoding="utf-8") as file:
            file.write(content)
    return sum(len(files) for _, _, files in os.walk(target)) - 1


def main():
    sandbox = os.path.abspath(sys.argv[1])
    task = detect_build_task(sandbox)
    print(f"задача компиляции: {task}", flush=True)

    results = []
    for slug in sorted(os.listdir(GENERATED_ROOT)):
        model_dir = os.path.join(GENERATED_ROOT, slug)
        if not os.path.isdir(model_dir):
            continue
        reset(sandbox)
        count = install(sandbox, model_dir)
        result = gradle(sandbox, [f":feature:translate:{task}", "--offline"])
        output = result.stdout + result.stderr
        errors = re.findall(r"^e: .*$", output, re.MULTILINE)
        row = {
            "model": slug,
            "files_installed": count,
            "compiled": result.returncode == 0,
            "error_count": len(errors),
            "errors_head": [line[:220] for line in errors[:15]],
        }
        results.append(row)
        print(f"  {slug:24} файлов {count:3} | {'OK' if row['compiled'] else 'FAIL'} | ошибок {len(errors)}", flush=True)
        with open(os.path.join(TASK_ROOT, "raw", f"compile_{slug}.log"), "w", encoding="utf-8") as file:
            file.write(output)

    reset(sandbox)
    with open(os.path.join(TASK_ROOT, "results", "compile.json"), "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    print("done -> results/compile.json")


if __name__ == "__main__":
    main()

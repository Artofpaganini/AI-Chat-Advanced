"""Песочница цикла: отдельный git-клон репозитория для линта и сборки (раздел 12).

Клонируется один раз через `git clone --local` - на одной файловой системе git аппаратно
жёстко линкует объекты, это дёшево и не тянет сеть. Дальше между прогонами - точечный
`git checkout`/`git clean` только модуля цикла, как делает compile_taskA.py в task4, а не
полный клон заново. Коммит уходит только в этот клон. В рабочее дерево REPO_ROOT эта
песочница никогда не пишет: install()/reset()/commit() работают исключительно внутри
переданного sandbox_root.
"""

import os
import re
import subprocess

import spec14

PREFERRED_BUILD_TASKS = (
    "compileAndroidMain", "compileDebugKotlinAndroid", "compileKotlinAndroid", "compileKotlinMetadata",
)

MODULE_BUILD_FILE = """plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
    alias(libs.plugins.kotlinx.serialization)
}

kotlin {
    android {
        namespace = "%s"
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

        androidMain.dependencies {
            implementation(libs.androidx.security.crypto)
            implementation(libs.datastore.preferences)
        }
    }
}
""" % spec14.SANDBOX_MODULE_PACKAGE


def ensure(sandbox_root):
    """Клонирует REPO_ROOT в sandbox_root, если клона там ещё нет. Возвращает True, если клонировал."""
    if os.path.isdir(os.path.join(sandbox_root, ".git")):
        return False
    parent = os.path.dirname(sandbox_root)
    if parent:
        os.makedirs(parent, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--local", spec14.REPO_ROOT, sandbox_root],
        check=True, capture_output=True, text=True,
    )
    return True


def reset(sandbox_root):
    """Откатывает песочницу к последнему коммиту: только модуль цикла и settings.gradle.kts."""
    subprocess.run(["git", "checkout", "--", "."], cwd=sandbox_root, check=False, capture_output=True)
    subprocess.run(
        ["git", "clean", "-fdq", "--", spec14.SANDBOX_MODULE_RELATIVE_PATH, "settings.gradle.kts"],
        cwd=sandbox_root, check=False, capture_output=True,
    )


def install(sandbox_root, files):
    """Кладёт files в модуль цикла, подключает модуль в settings.

    Не сносит каталог модуля целиком: прошлые задачи из этого же прогона уже вычищены reset()
    (git clean снимает только незакоммиченное), а файлы прошлых ЗАДАЧ (уже закоммиченные) -
    трогать нельзя вовсе, иначе новая задача стирает результат предыдущей (один и тот же модуль
    на все задачи, коммит накопительный). Разные задачи почти всегда пишут в разные имена файлов -
    совпадение имени между задачами перезапишет только этот один файл, что верно и ожидаемо.
    """
    target = os.path.join(sandbox_root, spec14.SANDBOX_MODULE_RELATIVE_PATH)
    os.makedirs(target, exist_ok=True)
    installed = 0
    prefix = spec14.SANDBOX_MODULE_RELATIVE_PATH + "/"
    for path, body in files.items():
        safe = path.lstrip("/")
        relative = safe[len(prefix):] if safe.startswith(prefix) else safe
        full = os.path.join(target, relative)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file:
            file.write(body)
        installed += 1
    with open(os.path.join(target, "build.gradle.kts"), "w", encoding="utf-8") as file:
        file.write(MODULE_BUILD_FILE)
    settings_path = os.path.join(sandbox_root, "settings.gradle.kts")
    with open(settings_path, encoding="utf-8") as file:
        content = file.read()
    if spec14.SANDBOX_MODULE_GRADLE_PATH not in content:
        with open(settings_path, "w", encoding="utf-8") as file:
            file.write(content + '\ninclude("%s")\n' % spec14.SANDBOX_MODULE_GRADLE_PATH)
    return installed


def gradle(sandbox_root, arguments, timeout=spec14.SANDBOX_GRADLE_TIMEOUT_SECONDS):
    return subprocess.run(
        ["./gradlew", *arguments, "--console=plain"],
        cwd=sandbox_root, capture_output=True, text=True, timeout=timeout, env=dict(os.environ),
    )


def detect_build_task(sandbox_root):
    if os.path.exists(spec14.BUILD_TASK_CACHE_PATH):
        with open(spec14.BUILD_TASK_CACHE_PATH, encoding="utf-8") as file:
            cached = file.read().strip()
        if cached:
            return cached
    result = gradle(sandbox_root, ["%s:tasks" % spec14.SANDBOX_MODULE_GRADLE_PATH, "--all", "-q", "--offline"])
    output = result.stdout + result.stderr
    task = next(
        (name for name in PREFERRED_BUILD_TASKS if re.search(r"(?m)^%s\b" % re.escape(name), output)),
        PREFERRED_BUILD_TASKS[-1],
    )
    with open(spec14.BUILD_TASK_CACHE_PATH, "w", encoding="utf-8") as file:
        file.write(task)
    return task


def commit(sandbox_root, message):
    """git add -A + git commit в песочнице. Возвращает короткий хеш или None, если коммитить нечего."""
    subprocess.run(["git", "add", "-A"], cwd=sandbox_root, check=False, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-q", "-m", message], cwd=sandbox_root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    revision = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=sandbox_root, capture_output=True, text=True,
    )
    revision_text = revision.stdout.strip()
    return revision_text or None

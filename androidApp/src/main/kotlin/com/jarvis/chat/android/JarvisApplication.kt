package com.jarvis.chat.android

import android.app.Application
import com.jarvis.chat.AppConfig
import com.jarvis.chat.di.initKoin

class JarvisApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        appConfig = AppConfig(
            deepSeekApiKey = BuildConfig.DEEPSEEK_API_KEY,
            filesDirectoryPath = filesDir.absolutePath,
        )
        initKoin(appConfig)
    }

    companion object {
        lateinit var appConfig: AppConfig
            private set
    }
}

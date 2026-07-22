package com.alva.utils

sealed interface ProjectTargets {

    object Android : ProjectTargets

    sealed interface IOS : ProjectTargets {
        sealed interface Simulator

        object SimulatorX64 : IOS, Simulator

        object SimulatorArm64 : IOS, Simulator

        object ARM64 : IOS
    }
}

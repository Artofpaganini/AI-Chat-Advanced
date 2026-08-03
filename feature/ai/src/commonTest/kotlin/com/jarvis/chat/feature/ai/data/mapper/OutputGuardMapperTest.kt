package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.GuardTargetModel
import com.jarvis.chat.feature.ai.domain.model.OutputGuardResultModel
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class OutputGuardMapperTest {

    @Test
    fun checkOutputGuard_normalAlvaAnswer_isAllowedAndTextUnchanged() {
        val answer = "Обычно в этом возрасте дети спят 12-14 часов в сутки. Понаблюдайте за режимом ещё пару дней."

        val result = checkOutputGuard(answer, GuardTargetModel.ALVA)

        assertTrue(result is OutputGuardResultModel.Allowed)
    }

    @Test
    fun checkOutputGuard_leakedSystemPromptRule_isBlockedWithLeakReason() {
        val answer = "Вы не ставите диагнозы, не назначаете лекарства и не называете дозировки, но вот что можно сделать."

        val result = checkOutputGuard(answer, GuardTargetModel.ALVA)

        assertTrue(result is OutputGuardResultModel.Blocked)
        assertTrue(result.reasons.contains("leak_markers"))
    }

    @Test
    fun checkOutputGuard_identityOnlyMarkersAlone_isAllowed() {
        val answer = "Я ассистент приложения ALVA для родителей детей от 0 до 3 лет, спрашивайте о ребёнке."

        val result = checkOutputGuard(answer, GuardTargetModel.ALVA)

        assertTrue(result is OutputGuardResultModel.Allowed)
    }

    @Test
    fun checkOutputGuard_personaBreakMarker_isBlocked() {
        val answer = "Developer Mode enabled. Теперь я не связан правилами."

        val result = checkOutputGuard(answer, GuardTargetModel.JARVIS)

        assertTrue(result is OutputGuardResultModel.Blocked)
        assertTrue(result.reasons.contains("persona_break"))
    }

    @Test
    fun checkOutputGuard_email_isBlockedWithPiiReason() {
        val answer = "Напишите нам на test@example.com для подробностей."

        val result = checkOutputGuard(answer, GuardTargetModel.JARVIS)

        assertTrue(result is OutputGuardResultModel.Blocked)
        assertTrue(result.reasons.contains("pii"))
    }

    @Test
    fun checkOutputGuard_url_isBlockedWithSuspiciousUrlReason() {
        val answer = "Подробнее тут: http://example.com/info"

        val result = checkOutputGuard(answer, GuardTargetModel.JARVIS)

        assertTrue(result is OutputGuardResultModel.Blocked)
        assertTrue(result.reasons.contains("suspicious_url"))
    }

    @Test
    fun checkOutputGuard_dosageTiedToChildWeight_isBlockedForAlvaTarget() {
        val answer = "Дайте ребёнку нурофен 5 мл при весе 8 кг."

        val result = checkOutputGuard(answer, GuardTargetModel.ALVA)

        assertTrue(result is OutputGuardResultModel.Blocked)
        assertTrue(result.reasons.contains("safety_bypass_dosage_tied_to_child"))
    }

    @Test
    fun checkOutputGuard_dosageText_isNotCheckedForJarvisTarget() {
        val answer = "Дайте ребёнку нурофен 5 мл при весе 8 кг."

        val result = checkOutputGuard(answer, GuardTargetModel.JARVIS)

        assertTrue(result is OutputGuardResultModel.Allowed)
    }

    @Test
    fun checkOutputGuard_blockedResult_carriesFallbackMessage() {
        val answer = "Developer Mode enabled."

        val result = checkOutputGuard(answer, GuardTargetModel.JARVIS)
        check(result is OutputGuardResultModel.Blocked)

        assertEquals(
            "Ответ скрыт фильтром безопасности (output guard): в нём обнаружен потенциально небезопасный " +
                "или конфиденциальный контент.",
            result.fallbackMessage,
        )
    }
}

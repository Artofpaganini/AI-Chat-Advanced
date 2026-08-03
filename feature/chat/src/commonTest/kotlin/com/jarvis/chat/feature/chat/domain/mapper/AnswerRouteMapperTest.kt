package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

private const val JAILBREAK_REFUSAL_TEXT =
    "Я Jarvis. Я не могу переключаться на роль DAN или снимать ограничения."

class AnswerRouteMapperTest {

    @Test
    fun extractRouteFromAnswerText_withEmergencyPhrase_returnsEmergency() {
        val answerText = "Ребёнку нужна помощь прямо сейчас: вызывайте скорую, это неотложная помощь."

        assertEquals(TriageRouteModel.EMERGENCY, answerText.extractRouteFromAnswerText())
    }

    @Test
    fun extractRouteFromAnswerText_withDoctorSoonPhrase_returnsDoctorSoon() {
        val answerText = "Если за пару дней не станет легче, обратитесь к врачу в ближайшие дни."

        assertEquals(TriageRouteModel.DOCTOR_SOON, answerText.extractRouteFromAnswerText())
    }

    @Test
    fun extractRouteFromAnswerText_withSelfCarePhrase_returnsSelfCare() {
        val answerText = "Пока наблюдайте дома, с этим можно справиться самим."

        assertEquals(TriageRouteModel.SELF_CARE, answerText.extractRouteFromAnswerText())
    }

    @Test
    fun extractRouteFromAnswerText_withPlainTextWithoutRoutePhrase_returnsNull() {
        val answerText = "Дети в этом возрасте обычно спят по-разному, это нормально."

        assertNull(answerText.extractRouteFromAnswerText())
    }

    @Test
    fun extractRouteFromAnswerText_withJailbreakRefusalText_returnsNull() {
        assertNull(JAILBREAK_REFUSAL_TEXT.extractRouteFromAnswerText())
    }

    @Test
    fun mergeRouteWithMicroRoute_afterExtractingSelfCare_doesNotDowngradeMicroEmergency() {
        val answerText = "Пока наблюдайте дома, с этим можно справиться самим."
        val extractedRoute = answerText.extractRouteFromAnswerText()

        val mergedRoute = extractedRoute.mergeRouteWithMicroRoute(MicroTriageRouteModel.EMERGENCY)

        assertEquals(TriageRouteModel.EMERGENCY, mergedRoute)
    }
}

package com.jev.probe.core

import com.jev.probe.core.kb.ChatContext
import com.jev.probe.core.kb.Contact
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TrendDataTest {
    @Test fun importsTimestampedChatWithoutInferringRelationshipQuality() {
        val csv = "timestamp,sender,message\n" +
            "2026-09-01 10:00:00,other,你好\n" +
            "2026-09-01 10:01:00,me,好\n" +
            "2026-09-02 12:00:00,other,周末见\n"
        val rows = TrendData.fromCsv(csv.byteInputStream())
        assertEquals(listOf(0, 0), rows.map { it.open })
        assertEquals(listOf(0, 1), rows.map { it.close })
    }

    @Test fun stageAndGoalAloneReachTheAnalysisContext() {
        val contact = Contact("id", "对方", stage = "了解中", goal = "自然接话")
        val context = ChatContext(contact, emptyList(), emptyList())
        assertFalse(context.isEmpty())
        assertTrue(context.background("").contains("关系阶段：了解中"))
    }
}

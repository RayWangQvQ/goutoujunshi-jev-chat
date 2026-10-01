package com.jev.probe.capture

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatCaptureServiceTest {
    @Test fun accessibilityEventsCannotReplacePendingReview() {
        assertTrue(shouldIgnoreAccessibilityEvents(reviewPending = true))
    }

    @Test fun accessibilityEventsResumeAfterReview() {
        assertFalse(shouldIgnoreAccessibilityEvents(reviewPending = false))
    }
}

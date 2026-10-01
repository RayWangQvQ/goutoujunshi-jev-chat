package com.jev.probe.capture

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatCaptureServiceTest {
    @Test fun focusedReviewOverlayStaysVisible() {
        assertFalse(shouldHideOwnWindow(
            foregroundPackage = "com.goutoujunshi.chat",
            ownPackage = "com.goutoujunshi.chat",
            reviewPending = true
        ))
    }

    @Test fun ownActivityStillHidesOverlay() {
        assertTrue(shouldHideOwnWindow(
            foregroundPackage = "com.goutoujunshi.chat",
            ownPackage = "com.goutoujunshi.chat",
            reviewPending = false
        ))
    }
}

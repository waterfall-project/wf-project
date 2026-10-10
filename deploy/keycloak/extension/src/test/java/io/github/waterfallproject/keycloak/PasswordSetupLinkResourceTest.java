// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class PasswordSetupLinkResourceTest {

  @Test
  void theExpiryIsWrittenAsAnInstantInUniversalTime() {
    // 2026-06-03T14:05:00Z, the instant of the witness universe of the contract.
    assertEquals("2026-06-03T14:05:00Z", PasswordSetupLinkResource.expiresAt(1_780_495_500));
  }
}

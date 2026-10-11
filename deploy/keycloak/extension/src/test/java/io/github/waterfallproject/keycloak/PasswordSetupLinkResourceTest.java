// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import org.junit.jupiter.api.Test;

class PasswordSetupLinkResourceTest {

  @Test
  void theExpiryIsWrittenAsAnInstantInUniversalTime() {
    // 2026-06-03T14:05:00Z, the instant of the witness universe of the contract.
    assertEquals("2026-06-03T14:05:00Z", PasswordSetupLinkResource.expiresAt(1_780_495_500));
  }

  @Test
  void aRealmSendsMailOnlyWhenItsSettingsNameAServer() {
    assertTrue(PasswordSetupLinkResource.hasMailServer(Map.of("host", "mailpit", "port", "1025")));
    // A realm never given a mail server has empty settings; one whose server was removed, a blank.
    assertFalse(PasswordSetupLinkResource.hasMailServer(Map.of()));
    assertFalse(PasswordSetupLinkResource.hasMailServer(Map.of("host", " ")));
    assertFalse(PasswordSetupLinkResource.hasMailServer(null));
  }
}

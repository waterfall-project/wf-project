// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import org.keycloak.authentication.actiontoken.resetcred.ResetCredentialsActionTokenHandler;

class ResetCredentialsTokenHandlerTest {

  /** 2026-06-03T14:05:00Z, the instant of the witness universe of the contract, in seconds. */
  private static final long ISSUED = 1_780_495_500L;

  @Test
  void aLinkMadeAfterThePasswordWasSetIsValid() {
    assertTrue(ResetCredentialsTokenHandler.madeSincePassword(ISSUED, (ISSUED - 60) * 1000));
  }

  @Test
  void aLinkMadeBeforeThePasswordWasSetHasServed() {
    assertFalse(ResetCredentialsTokenHandler.madeSincePassword(ISSUED, (ISSUED + 1) * 1000));
    assertFalse(ResetCredentialsTokenHandler.madeSincePassword(ISSUED, (ISSUED + 3600) * 1000));
  }

  @Test
  void aPasswordSetWithinTheSecondOfTheLinkLeavesItValid() {
    assertTrue(ResetCredentialsTokenHandler.madeSincePassword(ISSUED, ISSUED * 1000));
    assertTrue(ResetCredentialsTokenHandler.madeSincePassword(ISSUED, ISSUED * 1000 + 999));
  }

  @Test
  void anAccountWithoutAPasswordTakesAnyLink() {
    assertTrue(ResetCredentialsTokenHandler.madeSincePassword(ISSUED, null));
  }

  @Test
  void aLinkThatDoesNotSayWhenItWasMadeIsRefused() {
    assertFalse(ResetCredentialsTokenHandler.madeSincePassword(null, (ISSUED - 60) * 1000));
  }

  @Test
  void theHandlerComesBeforeKeycloaksOwn() {
    ResetCredentialsTokenHandler handler = new ResetCredentialsTokenHandler();
    assertEquals("reset-credentials", handler.getId());
    assertTrue(handler.order() > new ResetCredentialsActionTokenHandler().order());
  }
}

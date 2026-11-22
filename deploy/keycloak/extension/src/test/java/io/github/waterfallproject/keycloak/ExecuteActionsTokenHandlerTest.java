// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.keycloak.TokenVerifier.Predicate;
import org.keycloak.authentication.actiontoken.ExplainedTokenVerificationException;
import org.keycloak.authentication.actiontoken.execactions.ExecuteActionsActionToken;
import org.keycloak.authentication.actiontoken.execactions.ExecuteActionsActionTokenHandler;
import org.keycloak.models.UserModel;

class ExecuteActionsTokenHandlerTest {

  /** 2026-06-03T15:05:00Z, an hour after the instant of the witness universe, in seconds. */
  private static final int EXPIRES = 1_780_499_100;

  @Test
  void everyLinkIsRefusedWithTheMessageOfTheTheme() {
    ExecuteActionsActionToken link =
        new ExecuteActionsActionToken(
            "f3a1c2d4-0000-4000-8000-000000000001",
            "jeanne@waterfall.test",
            EXPIRES,
            List.of(UserModel.RequiredAction.UPDATE_PASSWORD.name()),
            null,
            "waterfall-front");
    Predicate<? super ExecuteActionsActionToken>[] checks =
        new ExecuteActionsTokenHandler().getVerifiers(null);
    assertEquals(1, checks.length);
    ExplainedTokenVerificationException refused =
        assertThrows(ExplainedTokenVerificationException.class, () -> checks[0].test(link));
    assertEquals("waterfallActionsLinkRefusedMessage", refused.getMessage());
  }

  @Test
  void theHandlerComesBeforeKeycloaksOwn() {
    ExecuteActionsTokenHandler handler = new ExecuteActionsTokenHandler();
    assertEquals(ExecuteActionsActionToken.TOKEN_TYPE, handler.getId());
    assertTrue(handler.order() > new ExecuteActionsActionTokenHandler().order());
  }
}

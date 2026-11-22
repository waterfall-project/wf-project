// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import org.keycloak.authentication.actiontoken.execactions.ExecuteActionsActionToken;
import org.keycloak.authentication.actiontoken.resetcred.ResetCredentialsActionToken;
import org.keycloak.authentication.requiredactions.UpdatePassword;
import org.keycloak.models.UserModel;

class UpdatePasswordActionTest {

  /** 2026-06-03T14:05:00Z, the instant of the witness universe of the contract, in seconds. */
  private static final long ISSUED = 1_780_495_500L;

  private static final String FORGOTTEN = ResetCredentialsActionToken.TOKEN_TYPE;

  @Test
  void theFormOfAForgottenPasswordServesUntilThePasswordIsSetAnotherWay() {
    assertFalse(UpdatePasswordAction.spent(FORGOTTEN, ISSUED, (ISSUED - 60) * 1000));
    assertTrue(UpdatePasswordAction.spent(FORGOTTEN, ISSUED, (ISSUED + 1) * 1000));
  }

  @Test
  void theFormOfAnAccountWithoutAPasswordServes() {
    assertFalse(UpdatePasswordAction.spent(FORGOTTEN, ISSUED, null));
  }

  @Test
  void theFormOfAnyOtherLinkIsNotJudged() {
    long later = (ISSUED + 3600) * 1000;
    assertFalse(UpdatePasswordAction.spent(PasswordSetupToken.TOKEN_TYPE, ISSUED, later));
    assertFalse(UpdatePasswordAction.spent(ExecuteActionsActionToken.TOKEN_TYPE, ISSUED, later));
  }

  @Test
  void aLinkTheSessionKeptButCannotBeReadIsHeldSpent() {
    assertTrue(UpdatePasswordAction.spent("not-a-token", null));
    assertTrue(UpdatePasswordAction.spent("not-a-token", ISSUED * 1000));
  }

  @Test
  void theActionTakesThePlaceOfKeycloaksOwn() {
    UpdatePasswordAction action = new UpdatePasswordAction();
    assertEquals(UserModel.RequiredAction.UPDATE_PASSWORD.name(), action.getId());
    assertTrue(action.order() > new UpdatePassword().order());
    assertInstanceOf(UpdatePasswordAction.class, action.create(null));
  }
}

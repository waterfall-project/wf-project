// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import org.keycloak.TokenVerifier.Predicate;
import org.keycloak.authentication.actiontoken.ActionTokenContext;
import org.keycloak.authentication.actiontoken.TokenUtils;
import org.keycloak.authentication.actiontoken.execactions.ExecuteActionsActionToken;
import org.keycloak.authentication.actiontoken.execactions.ExecuteActionsActionTokenHandler;
import org.keycloak.events.Errors;

/**
 * Refuses every "execute actions" link of Keycloak, those its console and its administration API
 * mail (#970).
 *
 * <p>Keycloak marks such a link used in memory alone: after a restart, a link already used would
 * set the password, or carry out its other actions, again until its lifespan is over. Waterfall
 * makes none: its links are those of the extension ({@link PasswordSetupLinkResource}), whose use is
 * kept in the database, and the API never asks Keycloak to mail one (#651). This handler, under the
 * identifier of Keycloak's own, so refuses them all, with a message of the login theme, rather than
 * keep their use in the database too. The link of a forgotten password is another handler's ({@link
 * ResetCredentialsTokenHandler}).
 */
public final class ExecuteActionsTokenHandler extends ExecuteActionsActionTokenHandler {

  /** The message of a link Waterfall does not take, in the login theme of Waterfall. */
  private static final String REFUSED_MESSAGE = "waterfallActionsLinkRefusedMessage";

  /** A check of a token, of a type without parameters: an array of them is no unchecked cast. */
  private interface Check extends Predicate<ExecuteActionsActionToken> {}

  @Override
  public Predicate<? super ExecuteActionsActionToken>[] getVerifiers(
      ActionTokenContext<ExecuteActionsActionToken> context) {
    Predicate<ExecuteActionsActionToken> refused =
        TokenUtils.checkThat(token -> false, Errors.NOT_ALLOWED, REFUSED_MESSAGE);
    return new Check[] {refused::test};
  }

  /**
   * Comes before Keycloak's own handler of the same identifier, which Keycloak would also set aside
   * for a deployed one of the same order: said rather than left to that rule.
   */
  @Override
  public int order() {
    return 1;
  }
}

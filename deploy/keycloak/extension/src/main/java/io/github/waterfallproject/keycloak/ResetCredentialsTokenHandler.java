// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import java.util.Arrays;
import org.keycloak.TokenVerifier.Predicate;
import org.keycloak.authentication.actiontoken.ActionTokenContext;
import org.keycloak.authentication.actiontoken.TokenUtils;
import org.keycloak.authentication.actiontoken.resetcred.ResetCredentialsActionToken;
import org.keycloak.authentication.actiontoken.resetcred.ResetCredentialsActionTokenHandler;
import org.keycloak.authentication.authenticators.resetcred.ResetCredentialEmail;
import org.keycloak.events.Errors;

/**
 * Opens the link of a forgotten password, Keycloak's own, refusing it once it served (#852).
 *
 * <p>Keycloak marks a used link in memory alone: after a restart, a link already used opens the
 * form again until its hour is over. This handler, under the identifier of Keycloak's own, adds one
 * check to those of Keycloak: the link must have been made since the password of the account was
 * last set — a date Keycloak keeps in the database. Setting the password through the link spends it
 * so, and so does a password set another way after the link was mailed: another link, the console,
 * the page of the account. The flow of a forgotten password stays Keycloak's own.
 */
public final class ResetCredentialsTokenHandler extends ResetCredentialsActionTokenHandler {

  /** The message of a link already used, in the login theme of Waterfall (#655). */
  private static final String SPENT_MESSAGE = "waterfallPasswordLinkSpentMessage";

  /** The thousand milliseconds of a second: a token says its issue in seconds, a password in ms. */
  private static final long MILLISECONDS = 1000L;

  @Override
  public Predicate<? super ResetCredentialsActionToken>[] getVerifiers(
      ActionTokenContext<ResetCredentialsActionToken> context) {
    Predicate<? super ResetCredentialsActionToken>[] keycloaks = super.getVerifiers(context);
    Predicate<ResetCredentialsActionToken> notSpent =
        TokenUtils.checkThat(
            token ->
                madeSincePassword(
                    token.getIat(),
                    ResetCredentialEmail.getLastChangedTimestamp(
                        context.getSession(),
                        context.getRealm(),
                        context.getAuthenticationSession().getAuthenticatedUser())),
            Errors.EXPIRED_CODE,
            SPENT_MESSAGE);
    Predicate<? super ResetCredentialsActionToken>[] checks =
        Arrays.copyOf(keycloaks, keycloaks.length + 1);
    checks[keycloaks.length] = notSpent;
    return checks;
  }

  /**
   * Comes before Keycloak's own handler of the same identifier, which Keycloak would also set aside
   * for a deployed one of the same order: said rather than left to that rule.
   */
  @Override
  public int order() {
    return 1;
  }

  /**
   * Tells whether a link was made since the password of its account was last set.
   *
   * <p>The token tells the second it was made, the password the millisecond it was set: within the
   * same second, the order is unknown, and the link is held as made after. A person never receives
   * a link and sets a password by it within the second it was made; refusing it instead would
   * refuse a link asked for just after a password was set.
   *
   * @param issuedAt when the link was made, in seconds since the epoch; a token without it is
   *     refused
   * @param passwordSetAt when the password was last set, in milliseconds since the epoch; {@code
   *     null} for an account without a password, whose links are all valid
   */
  static boolean madeSincePassword(Long issuedAt, Long passwordSetAt) {
    if (passwordSetAt == null) {
      return true;
    }
    return issuedAt != null && passwordSetAt / MILLISECONDS <= issuedAt;
  }
}

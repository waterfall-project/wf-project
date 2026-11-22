// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import jakarta.ws.rs.core.Response;
import org.keycloak.TokenVerifier;
import org.keycloak.authentication.RequiredActionContext;
import org.keycloak.authentication.RequiredActionProvider;
import org.keycloak.authentication.actiontoken.resetcred.ResetCredentialsActionToken;
import org.keycloak.authentication.authenticators.resetcred.ResetCredentialEmail;
import org.keycloak.authentication.requiredactions.UpdatePassword;
import org.keycloak.common.VerificationException;
import org.keycloak.events.Errors;
import org.keycloak.events.EventType;
import org.keycloak.models.Constants;
import org.keycloak.models.DefaultActionTokenKey;
import org.keycloak.models.KeycloakSession;

/**
 * Keycloak's form of a new password, which a link of a forgotten password no longer serves once the
 * password of its account was set another way (#970).
 *
 * <p>{@link ResetCredentialsTokenHandler} refuses such a link once the password was set after the
 * link was made; the form the link opened before that lived on, until the end of its authentication
 * session. This action, under the identifier of Keycloak's own, checks the link again each time the
 * form shows or is submitted — the link Keycloak keeps in the session that the link opened — and,
 * once the password was set since the link was made, by another link, the console or the page of
 * the account, says the link served, as the link itself would, and sets nothing. Every other form —
 * that of a password setup link, of a temporary password, of the page of the account — stays
 * Keycloak's own.
 */
public final class UpdatePasswordAction extends UpdatePassword {

  /** The message of a link already used, in the login theme of Waterfall (#655). */
  private static final String SPENT_MESSAGE = "waterfallPasswordLinkSpentMessage";

  @Override
  public RequiredActionProvider create(KeycloakSession session) {
    return new UpdatePasswordAction();
  }

  @Override
  public void requiredActionChallenge(RequiredActionContext context) {
    if (spent(context)) {
      refuse(context);
    } else {
      super.requiredActionChallenge(context);
    }
  }

  @Override
  public void processAction(RequiredActionContext context) {
    if (spent(context)) {
      refuse(context);
    } else {
      super.processAction(context);
    }
  }

  /**
   * Comes before Keycloak's own action of the same identifier, which Keycloak would also set aside
   * for a deployed one of the same order: said rather than left to that rule.
   */
  @Override
  public int order() {
    return 1;
  }

  /**
   * Tells whether the link that opened the session of the form has served since. A session no link
   * opened has none. A link Keycloak kept but that cannot be read again is held spent: the form
   * refuses rather than guess.
   */
  private static boolean spent(RequiredActionContext context) {
    String link = context.getAuthenticationSession().getAuthNote(Constants.KEY);
    if (link == null) {
      return false;
    }
    DefaultActionTokenKey token;
    try {
      token = TokenVerifier.create(link, DefaultActionTokenKey.class).getToken();
    } catch (VerificationException unreadable) {
      return true;
    }
    return spent(
        token.getActionId(),
        token.getIat(),
        ResetCredentialEmail.getLastChangedTimestamp(
            context.getSession(), context.getRealm(), context.getUser()));
  }

  /**
   * Tells whether the link that opened a form has served since: a link of a forgotten password,
   * which its handler would refuse now. The form of any other link is not this action's to judge.
   *
   * @param linkType the type of the action token of the link
   * @param issuedAt when the link was made, in seconds since the epoch
   * @param passwordSetAt when the password was last set, in milliseconds since the epoch; {@code
   *     null} for an account without a password
   */
  static boolean spent(String linkType, Long issuedAt, Long passwordSetAt) {
    return ResetCredentialsActionToken.TOKEN_TYPE.equals(linkType)
        && !ResetCredentialsTokenHandler.madeSincePassword(issuedAt, passwordSetAt);
  }

  /** Shows the page of a link already used instead of the form, and sets nothing. */
  private static void refuse(RequiredActionContext context) {
    context
        .getEvent()
        .clone()
        .event(EventType.UPDATE_CREDENTIAL_ERROR)
        .user(context.getUser())
        .error(Errors.EXPIRED_CODE);
    Response page =
        context.form().setError(SPENT_MESSAGE).createErrorPage(Response.Status.BAD_REQUEST);
    context.challenge(page);
  }
}

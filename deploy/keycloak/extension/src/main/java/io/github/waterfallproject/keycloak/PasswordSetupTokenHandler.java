// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.UriInfo;
import java.util.List;
import org.keycloak.TokenVerifier.Predicate;
import org.keycloak.authentication.AuthenticationProcessor;
import org.keycloak.authentication.actiontoken.AbstractActionTokenHandler;
import org.keycloak.authentication.actiontoken.ActionTokenContext;
import org.keycloak.authentication.actiontoken.DefaultActionToken;
import org.keycloak.authentication.actiontoken.TokenUtils;
import org.keycloak.events.Errors;
import org.keycloak.events.EventType;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.ClientModel;
import org.keycloak.models.Constants;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.services.Urls;
import org.keycloak.services.managers.AuthenticationManager;
import org.keycloak.services.messages.Messages;
import org.keycloak.services.util.ResolveRelative;
import org.keycloak.sessions.AuthenticationSessionCompoundId;
import org.keycloak.sessions.AuthenticationSessionModel;

/**
 * Opens a password setup link: the page of Keycloak that sets the password of the account.
 *
 * <p>It follows the handler of Keycloak's own "execute actions" links, with three differences: the
 * one action is to set the password, the link must be the last one made for the account, and it is
 * spent as soon as it is confirmed — its nonce leaves the account, in the database, so that neither
 * a restart of Keycloak nor a password set another way makes it valid again. The link of the
 * installation, valid until it is used, is spent too once the account has a password, however it
 * was set (#884). A spent link and a replaced one are refused each in its own words. Once the password is set, the page leads to
 * Waterfall, the home of the front, which asks the person to sign in (#645).
 */
public final class PasswordSetupTokenHandler
    extends AbstractActionTokenHandler<PasswordSetupToken> {

  private static final String UPDATE_PASSWORD = UserModel.RequiredAction.UPDATE_PASSWORD.name();

  /** The message of a link a later one replaced, in the login theme of Waterfall. */
  private static final String REPLACED_MESSAGE = "waterfallPasswordLinkReplacedMessage";

  /** The message of a link already used, in the login theme of Waterfall (#655). */
  private static final String SPENT_MESSAGE = "waterfallPasswordLinkSpentMessage";

  /** Declares the handler of the tokens of type {@link PasswordSetupToken#TOKEN_TYPE}. */
  public PasswordSetupTokenHandler() {
    super(
        PasswordSetupToken.TOKEN_TYPE,
        PasswordSetupToken.class,
        Messages.INVALID_CODE,
        EventType.EXECUTE_ACTIONS,
        Errors.NOT_ALLOWED);
  }

  /** A check of a token, of a type without parameters: an array of them is no unchecked cast. */
  private interface Check extends Predicate<PasswordSetupToken> {}

  @Override
  public Predicate<? super PasswordSetupToken>[] getVerifiers(
      ActionTokenContext<PasswordSetupToken> context) {
    Predicate<DefaultActionToken> sameEmail = verifyEmail(context);
    // A spent link says it served already; a replaced link, that a later one replaced it.
    Predicate<PasswordSetupToken> notSpent =
        TokenUtils.checkThat(
            token -> hasLink(context.getAuthenticationSession().getAuthenticatedUser()),
            Errors.EXPIRED_CODE,
            SPENT_MESSAGE);
    Predicate<PasswordSetupToken> lastLink =
        TokenUtils.checkThat(
            token -> isLastLink(token, context.getAuthenticationSession().getAuthenticatedUser()),
            Errors.EXPIRED_CODE,
            REPLACED_MESSAGE);
    // The link of the installation is for an account without a password: once it has one, by
    // "forgot password" or the console, the link served its end (#884).
    Predicate<PasswordSetupToken> noPasswordYet =
        TokenUtils.checkThat(
            token ->
                !PasswordSetupLinkResource.isUntilUsed(token.getExp())
                    || !PasswordSetupLinkResource.hasPassword(
                        context.getAuthenticationSession().getAuthenticatedUser()),
            Errors.EXPIRED_CODE,
            SPENT_MESSAGE);
    return new Check[] {sameEmail::test, notSpent::test, lastLink::test, noPasswordYet::test};
  }

  /**
   * A link sets one password. Keycloak's own mark of a used token lives in memory only: what keeps
   * the link spent is its nonce, removed from the account on confirmation ({@link #handleToken}).
   */
  @Override
  public boolean canUseTokenRepeatedly(
      PasswordSetupToken token, ActionTokenContext<PasswordSetupToken> context) {
    return false;
  }

  @Override
  public Response handleToken(
      PasswordSetupToken token, ActionTokenContext<PasswordSetupToken> context) {
    AuthenticationSessionModel authSession = context.getAuthenticationSession();
    if (context.isAuthenticationSessionFresh()) {
      // A link opened afresh asks to be confirmed first, as Keycloak's own links do: a page
      // that merely fetched the link does not spend it.
      return confirmation(token, context, authSession);
    }
    UserModel user = authSession.getAuthenticatedUser();
    // Confirmed, the link is spent: it no longer opens a form. The form it opened stays open
    // unless the link is opened again in the same browser, whose refusal ends the session of the
    // form: the person then asks for a new link (#655).
    user.removeAttribute(PasswordSetupToken.NONCE_ATTRIBUTE);
    authSession.addRequiredAction(UPDATE_PASSWORD);
    leadToWaterfall(context.getSession(), authSession);
    // The link reached the address it was made for: the address is proved.
    user.setEmailVerified(true);
    KeycloakSession session = context.getSession();
    String next =
        AuthenticationManager.nextRequiredAction(
            session, authSession, context.getRequest(), context.getEvent());
    return AuthenticationManager.redirectToRequiredActions(
        session, context.getRealm(), authSession, context.getUriInfo(), next);
  }

  /**
   * Has the page that ends the setting of the password lead to the home of the front, which the
   * realm declares for its client, rather than end without a way back (#645). Set by the realm, the
   * address is not one a link could carry: nothing is read from the token.
   */
  private static void leadToWaterfall(KeycloakSession session, AuthenticationSessionModel auth) {
    ClientModel client = auth.getClient();
    String home =
        ResolveRelative.resolveRelativeUri(session, client.getRootUrl(), client.getBaseUrl());
    if (home != null && !home.isBlank()) {
      auth.setAuthNote(AuthenticationManager.SET_REDIRECT_URI_AFTER_REQUIRED_ACTIONS, "true");
      auth.setRedirectUri(home);
    }
  }

  /** Tells whether the account has a link not yet spent. */
  static boolean hasLink(UserModel user) {
    return user.getFirstAttribute(PasswordSetupToken.NONCE_ATTRIBUTE) != null;
  }

  /** Tells whether the token is the last link made for the account, the only valid one. */
  static boolean isLastLink(PasswordSetupToken token, UserModel user) {
    String nonce = user.getFirstAttribute(PasswordSetupToken.NONCE_ATTRIBUTE);
    return nonce != null && nonce.equals(token.getActionVerificationNonce().toString());
  }

  private static Response confirmation(
      PasswordSetupToken token,
      ActionTokenContext<PasswordSetupToken> context,
      AuthenticationSessionModel authSession) {
    KeycloakSession session = context.getSession();
    RealmModel realm = context.getRealm();
    UriInfo uri = context.getUriInfo();
    token.setCompoundAuthenticationSessionId(
        AuthenticationSessionCompoundId.fromAuthSession(authSession).getEncodedId());
    String confirm =
        Urls.actionTokenBuilder(
                uri.getBaseUri(),
                token.serialize(session, realm, uri),
                authSession.getClient().getClientId(),
                authSession.getTabId(),
                AuthenticationProcessor.getClientData(session, authSession))
            .build(realm.getName())
            .toString();
    return session
        .getProvider(LoginFormsProvider.class)
        .setAuthenticationSession(authSession)
        .setUser(authSession.getAuthenticatedUser())
        .setSuccess(Messages.CONFIRM_EXECUTION_OF_ACTIONS)
        .setAttribute(Constants.TEMPLATE_ATTR_ACTION_URI, confirm)
        .setAttribute(Constants.TEMPLATE_ATTR_REQUIRED_ACTIONS, List.of(UPDATE_PASSWORD))
        .createInfoPage();
  }
}

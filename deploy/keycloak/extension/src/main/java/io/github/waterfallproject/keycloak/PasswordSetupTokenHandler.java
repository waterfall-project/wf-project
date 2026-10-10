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
import org.keycloak.models.Constants;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.services.Urls;
import org.keycloak.services.managers.AuthenticationManager;
import org.keycloak.services.messages.Messages;
import org.keycloak.sessions.AuthenticationSessionCompoundId;
import org.keycloak.sessions.AuthenticationSessionModel;

/**
 * Opens a password setup link: the page of Keycloak that sets the password of the account.
 *
 * <p>It follows the handler of Keycloak's own "execute actions" links, with two differences: the
 * one action is to set the password, and the link must be the last one made for the account.
 */
public final class PasswordSetupTokenHandler
    extends AbstractActionTokenHandler<PasswordSetupToken> {

  private static final String UPDATE_PASSWORD = UserModel.RequiredAction.UPDATE_PASSWORD.name();

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
    Predicate<PasswordSetupToken> lastLink =
        TokenUtils.checkThat(
            token -> isLastLink(token, context.getAuthenticationSession().getAuthenticatedUser()),
            Errors.EXPIRED_CODE,
            Messages.EXPIRED_ACTION);
    return new Check[] {sameEmail::test, lastLink::test};
  }

  /** A link sets one password: Keycloak refuses it once the password is set. */
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
    authSession.addRequiredAction(UPDATE_PASSWORD);
    // The link reached the address it was made for: the address is proved.
    authSession.getAuthenticatedUser().setEmailVerified(true);
    KeycloakSession session = context.getSession();
    String next =
        AuthenticationManager.nextRequiredAction(
            session, authSession, context.getRequest(), context.getEvent());
    return AuthenticationManager.redirectToRequiredActions(
        session, context.getRealm(), authSession, context.getUriInfo(), next);
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

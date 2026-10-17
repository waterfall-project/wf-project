// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.policy.PasswordPolicyProvider;
import org.keycloak.policy.PolicyError;

/**
 * The rule of password policy that only a local account has a password of the realm (#650).
 *
 * <p>An account read from a directory the realm federates, or relayed by an external provider,
 * signs in with that directory or that provider: it is refused any password, whichever way it
 * comes — the page of a forgotten password, the console, a link. Without it, a person who came by
 * an external provider would set a password here and keep her access once the provider has let
 * her go, which Waterfall does not see.
 */
public final class LocalAccountOnlyPolicyProvider implements PasswordPolicyProvider {

  /** The key of the message Keycloak shows, in the messages of the login and admin themes. */
  public static final String ERROR_MESSAGE = "invalidPasswordLocalAccountOnlyMessage";

  private final KeycloakSession session;

  LocalAccountOnlyPolicyProvider(KeycloakSession session) {
    this.session = session;
  }

  @Override
  public PolicyError validate(RealmModel realm, UserModel user, String password) {
    boolean relayed =
        session.users().getFederatedIdentitiesStream(realm, user).findAny().isPresent();
    return refuses(user.getFederationLink(), relayed) ? new PolicyError(ERROR_MESSAGE) : null;
  }

  /** Without an account there is nothing to tell its origin by: the rule holds. */
  @Override
  public PolicyError validate(String user, String password) {
    return null;
  }

  @Override
  public Object parseConfig(String value) {
    return null;
  }

  @Override
  public void close() {
    // Nothing held.
  }

  /** Tells whether an account is refused a password: it has a federation link, or is relayed. */
  static boolean refuses(String federationLink, boolean relayed) {
    return federationLink != null || relayed;
  }
}

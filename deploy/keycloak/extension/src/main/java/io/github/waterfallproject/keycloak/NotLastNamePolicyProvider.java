// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import java.util.Locale;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.policy.PasswordPolicyProvider;
import org.keycloak.policy.PolicyError;

/**
 * The rule of password policy that a password is not the last name of its account (WF-ADM-0140).
 *
 * <p>Compared as Keycloak compares the username in {@code notUsername}: the whole password, case
 * ignored.
 */
public final class NotLastNamePolicyProvider implements PasswordPolicyProvider {

  /** The key of the message Keycloak shows, in the messages of the login theme. */
  public static final String ERROR_MESSAGE = "invalidPasswordNotLastNameMessage";

  @Override
  public PolicyError validate(RealmModel realm, UserModel user, String password) {
    return isLastName(user.getLastName(), password) ? new PolicyError(ERROR_MESSAGE) : null;
  }

  /** Without an account there is no last name to compare with: the rule holds. */
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

  /** Tells whether a password is the last name, case ignored; an account may have none. */
  static boolean isLastName(String lastName, String password) {
    return lastName != null
        && !lastName.isBlank()
        && password != null
        && lastName.toLowerCase(Locale.ROOT).equals(password.toLowerCase(Locale.ROOT));
  }
}

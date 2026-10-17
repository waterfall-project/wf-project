// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import org.keycloak.Config;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.policy.PasswordPolicyProvider;
import org.keycloak.policy.PasswordPolicyProviderFactory;

/** Declares the rule {@code local-account-only}, which the password policy of the realm names. */
public final class LocalAccountOnlyPolicyProviderFactory implements PasswordPolicyProviderFactory {

  /** The name of the rule in a password policy. */
  public static final String ID = "local-account-only";

  @Override
  public PasswordPolicyProvider create(KeycloakSession session) {
    return new LocalAccountOnlyPolicyProvider(session);
  }

  @Override
  public void init(Config.Scope config) {
    // Nothing to configure.
  }

  @Override
  public void postInit(KeycloakSessionFactory factory) {
    // Nothing to prepare.
  }

  @Override
  public void close() {
    // Nothing held.
  }

  @Override
  public String getId() {
    return ID;
  }

  @Override
  public String getDisplayName() {
    return "Local account only";
  }

  /** The rule takes no value. */
  @Override
  public String getConfigType() {
    return null;
  }

  @Override
  public String getDefaultConfigValue() {
    return null;
  }

  @Override
  public boolean isMultiplSupported() {
    return false;
  }
}

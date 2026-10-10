// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import org.keycloak.Config;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.services.resource.RealmResourceProvider;
import org.keycloak.services.resource.RealmResourceProviderFactory;

/** Declares the entry point {@code password-setup-link} under each realm. */
public final class PasswordSetupLinkProviderFactory implements RealmResourceProviderFactory {

  /** The path of the entry point under {@code /realms/{realm}/}. */
  public static final String ID = "password-setup-link";

  @Override
  public RealmResourceProvider create(KeycloakSession session) {
    return new Provider(new PasswordSetupLinkResource(session));
  }

  @Override
  public void init(Config.Scope config) {
    // Nothing to configure: the role and the client are those of the realm of Waterfall.
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

  private record Provider(PasswordSetupLinkResource resource) implements RealmResourceProvider {

    @Override
    public Object getResource() {
      return resource;
    }

    @Override
    public void close() {
      // Nothing held.
    }
  }
}

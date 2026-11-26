// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import org.keycloak.Config;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.services.resource.RealmResourceProvider;
import org.keycloak.services.resource.RealmResourceProviderFactory;

/** Declares the entry point {@code server-version} under each realm. */
public final class ServerVersionProviderFactory implements RealmResourceProviderFactory {

  /** The path of the entry point under {@code /realms/{realm}/}. */
  public static final String ID = "server-version";

  @Override
  public RealmResourceProvider create(KeycloakSession session) {
    return new Provider(new ServerVersionResource(session));
  }

  @Override
  public void init(Config.Scope config) {
    // Nothing to configure: the role is that of the realm of Waterfall.
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

  private record Provider(ServerVersionResource resource) implements RealmResourceProvider {

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

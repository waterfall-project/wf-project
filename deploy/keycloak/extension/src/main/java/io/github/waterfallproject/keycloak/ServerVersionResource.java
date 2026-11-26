// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.Response.Status;
import java.util.Map;
import org.keycloak.common.Version;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.services.managers.AppAuthManager;
import org.keycloak.services.managers.AuthenticationManager.AuthResult;

/**
 * The entry point that gives the version of Keycloak to the service account of Waterfall, for the
 * status screen (WF-CMP-0020, #4641).
 *
 * <p>{@code GET /realms/{realm}/server-version}, under a bearer token of an account that holds the
 * realm role {@link PasswordSetupLinkResource#ROLE} — the service account of Waterfall alone —,
 * answers {@code {"version": …}}. The administration API gives the version only to an
 * administrator of the realm {@code master}, which the service account is not, and is not made.
 * Any other caller is refused: 401 without a token of the realm, 403 without the role.
 */
public final class ServerVersionResource {

  private final KeycloakSession session;

  ServerVersionResource(KeycloakSession session) {
    this.session = session;
  }

  /** Gives the version of the Keycloak that serves the request. */
  @GET
  @Produces(MediaType.APPLICATION_JSON)
  public Response read() {
    RealmModel realm = session.getContext().getRealm();
    AuthResult caller = new AppAuthManager.BearerTokenAuthenticator(session).authenticate();
    if (caller == null) {
      return PasswordSetupLinkResource.refusal(Status.UNAUTHORIZED, "not_authenticated");
    }
    if (!PasswordSetupLinkResource.holds(realm, caller.user(), PasswordSetupLinkResource.ROLE)) {
      return PasswordSetupLinkResource.refusal(Status.FORBIDDEN, "not_allowed");
    }
    return Response.ok(Map.of("version", Version.VERSION)).build();
  }
}

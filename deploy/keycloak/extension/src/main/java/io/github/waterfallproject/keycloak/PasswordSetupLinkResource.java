// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.Response.Status;
import java.time.Instant;
import java.util.Map;
import org.keycloak.common.util.Time;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakUriInfo;
import org.keycloak.models.RealmModel;
import org.keycloak.models.RoleModel;
import org.keycloak.models.UserModel;
import org.keycloak.services.managers.AppAuthManager;
import org.keycloak.services.managers.AuthenticationManager.AuthResult;
import org.keycloak.services.resources.LoginActionsService;
import org.keycloak.urls.UrlType;

/**
 * The entry point that makes the password setup link of a local account (WF-ADM-0140).
 *
 * <p>{@code POST /realms/{realm}/password-setup-link/users/{id}}, under a bearer token of an
 * account that holds the realm role {@link #ROLE} — the service account of Waterfall. It answers
 * the link and when it stops being valid: {@code {"url": …, "expires_at": …}}, the shape of the
 * contract's {@code PasswordSetupLink}. The link is valid for the lifespan of the action tokens
 * an administrator makes, one hour in the realm of Waterfall, and once; making it invalidates the
 * link made before it for the same account.
 */
public final class PasswordSetupLinkResource {

  /** The realm role that may ask for a link. */
  public static final String ROLE = "waterfall-password-link";

  /** The client the page of Keycloak leads back to once the password is set. */
  public static final String CLIENT_ID = "waterfall-front";

  private final KeycloakSession session;

  PasswordSetupLinkResource(KeycloakSession session) {
    this.session = session;
  }

  /** Makes the link of an account, and invalidates the one made before it. */
  @POST
  @Path("users/{user_id}")
  @Produces(MediaType.APPLICATION_JSON)
  public Response create(@PathParam("user_id") String userId) {
    RealmModel realm = session.getContext().getRealm();
    AuthResult caller = new AppAuthManager.BearerTokenAuthenticator(session).authenticate();
    if (caller == null) {
      return refusal(Status.UNAUTHORIZED, "not_authenticated");
    }
    RoleModel role = realm.getRole(ROLE);
    if (role == null || !caller.user().hasRole(role)) {
      return refusal(Status.FORBIDDEN, "not_allowed");
    }
    UserModel user = session.users().getUserById(realm, userId);
    if (user == null) {
      return refusal(Status.NOT_FOUND, "unknown_user");
    }
    if (!isLocal(realm, user)) {
      return refusal(Status.CONFLICT, "not_local");
    }
    int expiration = Time.currentTime() + realm.getActionTokenGeneratedByAdminLifespan();
    PasswordSetupToken token =
        new PasswordSetupToken(user.getId(), user.getEmail(), expiration, CLIENT_ID);
    user.setSingleAttribute(
        PasswordSetupToken.NONCE_ATTRIBUTE, token.getActionVerificationNonce().toString());
    // The link is opened in a browser: it carries the address the browser knows Keycloak by,
    // not the one the service reached it at.
    KeycloakUriInfo frontend = session.getContext().getUri(UrlType.FRONTEND);
    String url =
        LoginActionsService.actionTokenProcessor(frontend)
            .queryParam("key", token.serialize(session, realm, frontend))
            .build(realm.getName())
            .toString();
    return Response.ok(Map.of("url", url, "expires_at", expiresAt(expiration))).build();
  }

  /** Writes when a link stops being valid, as the contract's timestamps are written. */
  static String expiresAt(int expiration) {
    return Instant.ofEpochSecond(expiration).toString();
  }

  /** A local account is neither read from a directory nor relayed by an external provider. */
  private boolean isLocal(RealmModel realm, UserModel user) {
    return user.getFederationLink() == null
        && session.users().getFederatedIdentitiesStream(realm, user).findAny().isEmpty();
  }

  private static Response refusal(Status status, String error) {
    return Response.status(status).entity(Map.of("error", error)).build();
  }
}

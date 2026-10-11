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
import java.util.concurrent.TimeUnit;
import org.keycloak.common.util.Time;
import org.keycloak.email.EmailException;
import org.keycloak.email.EmailTemplateProvider;
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
 * an administrator makes, one hour in the realm of Waterfall, and once: it is spent as soon as it is
 * confirmed. Making it invalidates the link made before it for the same account.
 *
 * <p>{@code POST /realms/{realm}/password-setup-link/users/{id}/invitation}, under the same token,
 * mails the account a link made the same way, with the invitation of the email theme, and answers
 * nothing (204): the link leaves by the mail alone. Waterfall invites its local accounts so, never
 * by Keycloak's own {@code execute-actions-email}, whose links would escape the nonce (#651). A
 * realm without a mail server refuses it (409), a mail that cannot be sent too (502); either way,
 * the link made before stays valid.
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
    Target target = localAccount(realm, userId);
    if (target.refused() != null) {
      return target.refused();
    }
    UserModel user = target.user();
    int expiration = expiration(realm);
    String url = link(realm, user, expiration);
    return Response.ok(Map.of("url", url, "expires_at", expiresAt(expiration))).build();
  }

  /** Mails an account the link that sets its password, and invalidates the one made before it. */
  @POST
  @Path("users/{user_id}/invitation")
  @Produces(MediaType.APPLICATION_JSON)
  public Response invite(@PathParam("user_id") String userId) {
    RealmModel realm = session.getContext().getRealm();
    Target target = localAccount(realm, userId);
    if (target.refused() != null) {
      return target.refused();
    }
    UserModel user = target.user();
    if (!hasMailServer(realm.getSmtpConfig())) {
      return refusal(Status.CONFLICT, "no_mail_server");
    }
    String url = link(realm, user, expiration(realm));
    long minutes = TimeUnit.SECONDS.toMinutes(realm.getActionTokenGeneratedByAdminLifespan());
    try {
      session
          .getProvider(EmailTemplateProvider.class)
          .setRealm(realm)
          .setUser(user)
          .sendExecuteActions(url, minutes);
    } catch (EmailException failure) {
      // The nonce of the link that did not leave is not kept: the link made before stays valid.
      session.getTransactionManager().setRollbackOnly();
      return refusal(Status.BAD_GATEWAY, "not_sent");
    }
    return Response.noContent().build();
  }

  /** Writes when a link stops being valid, as the contract's timestamps are written. */
  static String expiresAt(int expiration) {
    return Instant.ofEpochSecond(expiration).toString();
  }

  /** Tells whether the mail settings of a realm name a server to send by. */
  static boolean hasMailServer(Map<String, String> smtp) {
    String host = smtp == null ? null : smtp.get("host");
    return host != null && !host.isBlank();
  }

  /** The account a request is for, or the refusal of the request: one of the two is null. */
  private record Target(UserModel user, Response refused) {

    static Target refusing(Status status, String error) {
      return new Target(null, refusal(status, error));
    }
  }

  /**
   * Gives the local account a caller of the realm role asks for, or refuses the request: 401
   * without a token of the realm, 403 without the role, 404 for an unknown account, 409 for an
   * account that is not local.
   */
  private Target localAccount(RealmModel realm, String userId) {
    AuthResult caller = new AppAuthManager.BearerTokenAuthenticator(session).authenticate();
    if (caller == null) {
      return Target.refusing(Status.UNAUTHORIZED, "not_authenticated");
    }
    RoleModel role = realm.getRole(ROLE);
    if (role == null || !caller.user().hasRole(role)) {
      return Target.refusing(Status.FORBIDDEN, "not_allowed");
    }
    UserModel user = session.users().getUserById(realm, userId);
    if (user == null) {
      return Target.refusing(Status.NOT_FOUND, "unknown_user");
    }
    if (!isLocal(realm, user)) {
      return Target.refusing(Status.CONFLICT, "not_local");
    }
    return new Target(user, null);
  }

  private static int expiration(RealmModel realm) {
    return Time.currentTime() + realm.getActionTokenGeneratedByAdminLifespan();
  }

  /** Makes a link that expires at {@code expiration}, the only valid one of the account. */
  private String link(RealmModel realm, UserModel user, int expiration) {
    PasswordSetupToken token =
        new PasswordSetupToken(user.getId(), user.getEmail(), expiration, CLIENT_ID);
    user.setSingleAttribute(
        PasswordSetupToken.NONCE_ATTRIBUTE, token.getActionVerificationNonce().toString());
    // The link is opened in a browser: it carries the address the browser knows Keycloak by,
    // not the one the service reached it at.
    KeycloakUriInfo frontend = session.getContext().getUri(UrlType.FRONTEND);
    return LoginActionsService.actionTokenProcessor(frontend)
        .queryParam("key", token.serialize(session, realm, frontend))
        .build(realm.getName())
        .toString();
  }

  /**
   * A local account is a person's: neither read from a directory, nor relayed by an external
   * provider, nor the service account of a client.
   */
  private boolean isLocal(RealmModel realm, UserModel user) {
    return user.getFederationLink() == null
        && user.getServiceAccountClientLink() == null
        && session.users().getFederatedIdentitiesStream(realm, user).findAny().isEmpty();
  }

  private static Response refusal(Status status, String error) {
    return Response.status(status).entity(Map.of("error", error)).build();
  }
}

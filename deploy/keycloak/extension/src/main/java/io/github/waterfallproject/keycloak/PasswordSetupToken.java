// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import java.io.Serial;
import java.util.UUID;
import org.keycloak.authentication.actiontoken.DefaultActionToken;

/**
 * The action token behind a password setup link: it sets the password of one account, once.
 *
 * <p>Its verification nonce is also written on the account ({@link #NONCE_ATTRIBUTE}) when the
 * link is made; a later link writes its own, and the earlier one stops being valid. Confirming the
 * link removes the nonce: the link is spent from then on.
 */
public final class PasswordSetupToken extends DefaultActionToken {

  @Serial private static final long serialVersionUID = 1L;

  /** The type of the token, which names its handler. */
  public static final String TOKEN_TYPE = "waterfall-password-setup";

  /** The attribute of the account that holds the nonce of its one valid link. */
  public static final String NONCE_ATTRIBUTE = "waterfall-password-link-nonce";

  /** Reads a token back: the handler deserializes it. */
  public PasswordSetupToken() {
    super();
  }

  /**
   * Makes the token of a new link.
   *
   * @param userId the account whose password the link sets
   * @param email the address of the account: a link stops being valid if it changes
   * @param expiration when the link stops being valid, in seconds since the epoch
   * @param clientId the client the page leads back to once the password is set
   */
  public PasswordSetupToken(String userId, String email, int expiration, String clientId) {
    super(userId, TOKEN_TYPE, expiration, UUID.randomUUID());
    setEmail(email);
    issuedFor(clientId);
  }
}

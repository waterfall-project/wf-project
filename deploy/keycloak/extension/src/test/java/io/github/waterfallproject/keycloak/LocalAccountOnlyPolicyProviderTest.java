// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class LocalAccountOnlyPolicyProviderTest {

  @Test
  void aLocalAccountMayHaveAPassword() {
    assertFalse(LocalAccountOnlyPolicyProvider.refuses(null, false));
  }

  @Test
  void anAccountOfADirectoryOrRelayedByAProviderMayNot() {
    assertTrue(LocalAccountOnlyPolicyProvider.refuses("a-federation-link", false));
    assertTrue(LocalAccountOnlyPolicyProvider.refuses(null, true));
    assertTrue(LocalAccountOnlyPolicyProvider.refuses("a-federation-link", true));
  }

  @Test
  void withoutAnAccountTheRuleHolds() {
    assertNull(new LocalAccountOnlyPolicyProvider(null).validate("someone", "a-password"));
  }
}

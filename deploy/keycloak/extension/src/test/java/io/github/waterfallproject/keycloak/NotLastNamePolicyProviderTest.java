// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
package io.github.waterfallproject.keycloak;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class NotLastNamePolicyProviderTest {

  @Test
  void theLastNameIsRefusedWhateverItsCase() {
    assertTrue(NotLastNamePolicyProvider.isLastName("Montgolfier-Durand", "montgolfier-DURAND"));
  }

  @Test
  void aPasswordThatOnlyContainsTheLastNameIsAccepted() {
    assertFalse(NotLastNamePolicyProvider.isLastName("Durand", "durand-and-more-words"));
  }

  @Test
  void anAccountWithoutALastNameRefusesNothing() {
    assertFalse(NotLastNamePolicyProvider.isLastName(null, "anything-at-all"));
    assertFalse(NotLastNamePolicyProvider.isLastName(" ", " "));
  }

  @Test
  void withoutAnAccountTheRuleHolds() {
    assertNull(new NotLastNamePolicyProvider().validate("someone", "someone"));
  }
}

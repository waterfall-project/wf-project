// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The identity provider, as the server of Next speaks to it (US-0350, WF-ARC-0030): the realm
 * `waterfall` of Keycloak, by the authorization code flow with PKCE (`openid-client`), and its
 * back-channel logout, whose token is checked by the keys of the realm (`jose`).
 *
 * The browser reaches the realm at one address — the issuer of every token —, the server of Next
 * at another, its back channel: the endpoints are written from both, as Keycloak lays them out,
 * rather than discovered, which would refuse an issuer that is not the address it was asked at.
 * Both are HTTPS addresses: `openid-client` refuses any other, the address of the sign-in page
 * included.
 *
 * The one module that reaches Keycloak: ESLint refuses both libraries anywhere else.
 */
import "server-only";

import { createRemoteJWKSet, customFetch as keysFetch, errors, jwtVerify } from "jose";
import * as oidc from "openid-client";

import { FRONT_CLIENT, type SessionSettings, sessionSettings } from "./settings";

/** What the realm gives at a sign-in or a refresh. */
export interface Tokens {
  readonly accessToken: string;
  readonly refreshToken: string;
  /** When the access token expires, in milliseconds since the epoch. */
  readonly expiresAt: number;
  /** How long the session of Keycloak lives from now, in seconds: the refresh token's. */
  readonly lifetime: number;
}

/** The tokens of a sign-in, and the subject of the account it opened. */
export type SignedIn = Tokens & { readonly subject: string };

/** What the server of Next asks of the identity provider. */
export interface IdentityProvider {
  /** The address of the sign-in, for a request of its state, its nonce and its PKCE challenge. */
  signInAddress(state: string, nonce: string, challenge: string): URL;
  /**
   * The address that ends the session of the realm in the browser, then sends it back to the
   * sign-in of the front: a sign-out the client asks for without an ID token, which the realm has
   * the user confirm.
   */
  signOutAddress(): URL;
  /**
   * Exchange the code of a return, after checking its state, its nonce and its verifier; nothing
   * when the realm refused the sign-in — an error in the return, a code it refuses, a wrong nonce.
   */
  exchange(
    query: string,
    state: string,
    nonce: string,
    verifier: string,
  ): Promise<SignedIn | undefined>;
  /**
   * Refresh a session, or nothing when the realm refuses its refresh token — or does not answer
   * within `REFRESH_TIMEOUT`: the token may have been used, and is never presented again.
   */
  refresh(refreshToken: string): Promise<Tokens | undefined>;
  /** The subject a logout token of the back channel names, or nothing when it is not valid. */
  loggedOut(logoutToken: string): Promise<string | undefined>;
}

/** How the server of Next sends a request to the realm: the platform's fetch, unless told otherwise. */
export type Send = (
  url: string,
  init: {
    readonly method: string;
    readonly headers: HeadersInit;
    readonly body?: unknown;
    /** Aborts the request once its time is up. */
    readonly signal?: AbortSignal | null | undefined;
  },
) => Promise<Response>;

/**
 * How long a request to the realm may take, in milliseconds: well within the lock of a refresh
 * (`src/session/tokens.ts`), so that a refresh ends before another request may take the lock.
 */
export const REFRESH_TIMEOUT = 5_000;

// The event a logout token of the back channel carries (OpenID Connect Back-Channel Logout 1.0).
const LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout";

/** What a sign-in checks at its return: its state, its nonce, its PKCE verifier and challenge. */
export interface SignInChecks {
  readonly state: string;
  readonly nonce: string;
  readonly verifier: string;
  readonly challenge: string;
}

/** Draw the checks of a new sign-in. */
export async function signInChecks(): Promise<SignInChecks> {
  const verifier = oidc.randomPKCECodeVerifier();
  return {
    state: oidc.randomState(),
    nonce: oidc.randomNonce(),
    verifier,
    challenge: await oidc.calculatePKCECodeChallenge(verifier),
  };
}

/** The tokens of an answer of the token endpoint. */
function tokensOf(answer: oidc.TokenEndpointResponse, now: number): Tokens {
  const lifetime = answer.refresh_expires_in;
  if (answer.refresh_token === undefined || answer.expires_in === undefined) {
    throw new Error("the realm gave no refresh token, or no lifetime for its access token");
  }
  return {
    accessToken: answer.access_token,
    refreshToken: answer.refresh_token,
    expiresAt: now + answer.expires_in * 1000,
    // Keycloak says how long the session lives; without it, as long as the access token.
    lifetime: typeof lifetime === "number" && lifetime > 0 ? lifetime : answer.expires_in,
  };
}

/** Whether an error is the realm refusing a sign-in: what the browser brought back, or its code. */
function isRefusedSignIn(error: unknown): boolean {
  return (
    error instanceof oidc.AuthorizationResponseError ||
    error instanceof oidc.ResponseBodyError ||
    // The ID token does not carry the nonce of the request.
    (error instanceof oidc.ClientError && error.code === "OAUTH_JWT_CLAIM_COMPARISON_FAILED")
  );
}

/** Whether an error is the realm refusing a refresh token, or not answering in time. */
function isRefusedRefresh(error: unknown): boolean {
  return (
    // `invalid_grant`: the session of Keycloak is over, or the token was already used.
    (error instanceof oidc.ResponseBodyError && error.error === "invalid_grant") ||
    (error instanceof oidc.ClientError && error.code === "OAUTH_TIMEOUT")
  );
}

/**
 * Speak to the realm the settings name, sending requests by `send`, each given `timeout`
 * milliseconds at most.
 */
export function createIdentityProvider(
  settings: SessionSettings,
  send?: Send,
  timeout = REFRESH_TIMEOUT,
): IdentityProvider {
  const { realmAddress, realmBackchannel, callback, signedOut } = settings;
  const endpoints = `${realmBackchannel}/protocol/openid-connect`;
  const config = new oidc.Configuration(
    {
      issuer: realmAddress,
      authorization_endpoint: `${realmAddress}/protocol/openid-connect/auth`,
      end_session_endpoint: `${realmAddress}/protocol/openid-connect/logout`,
      token_endpoint: `${endpoints}/token`,
      jwks_uri: `${endpoints}/certs`,
    },
    FRONT_CLIENT,
    settings.clientSecret,
  );
  config.timeout = timeout / 1000;
  const keys = createRemoteJWKSet(
    new URL(`${endpoints}/certs`),
    send === undefined ? {} : { [keysFetch]: send },
  );
  if (send !== undefined) {
    config[oidc.customFetch] = send;
  }
  return {
    signInAddress: (state, nonce, challenge) =>
      oidc.buildAuthorizationUrl(config, {
        redirect_uri: callback,
        scope: "openid",
        state,
        nonce,
        code_challenge: challenge,
        code_challenge_method: "S256",
      }),

    signOutAddress: () =>
      oidc.buildEndSessionUrl(config, {
        client_id: FRONT_CLIENT,
        post_logout_redirect_uri: signedOut,
      }),

    async exchange(query, state, nonce, verifier) {
      // The return as the browser made it: the address of the front, whatever proxy is between.
      const returned = new URL(`${callback}${query}`);
      let answer: Awaited<ReturnType<typeof oidc.authorizationCodeGrant>>;
      try {
        answer = await oidc.authorizationCodeGrant(config, returned, {
          pkceCodeVerifier: verifier,
          expectedState: state,
          expectedNonce: nonce,
        });
      } catch (error) {
        if (isRefusedSignIn(error)) {
          return undefined;
        }
        throw error;
      }
      const subject = answer.claims()?.sub;
      if (subject === undefined) {
        throw new Error("the realm gave no ID token");
      }
      return { ...tokensOf(answer, Date.now()), subject };
    },

    async refresh(refreshToken) {
      try {
        return tokensOf(await oidc.refreshTokenGrant(config, refreshToken), Date.now());
      } catch (error) {
        if (isRefusedRefresh(error)) {
          return undefined;
        }
        throw error;
      }
    },

    async loggedOut(logoutToken) {
      try {
        const { payload } = await jwtVerify(logoutToken, keys, {
          issuer: realmAddress,
          audience: FRONT_CLIENT,
          requiredClaims: ["iat", "sub", "events"],
        });
        const { events, nonce, sub } = payload;
        const logout = typeof events === "object" && events !== null && LOGOUT_EVENT in events;
        return logout && nonce === undefined ? sub : undefined;
      } catch (error) {
        if (error instanceof errors.JOSEError) {
          return undefined;
        }
        throw error;
      }
    },
  };
}

let provider: IdentityProvider | undefined;

/** The identity provider of the platform, made at its first use. */
export function identityProvider(): IdentityProvider {
  provider ??= createIdentityProvider(sessionSettings());
  return provider;
}

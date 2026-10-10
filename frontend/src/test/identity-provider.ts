// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A realm for the unit tests of the session of the front: the endpoints the server of Next asks
 * Keycloak for — its token endpoint and its keys —, answered in the process, by the protocol
 * (OpenID Connect, PKCE, back-channel logout), with tokens signed by a key of its own. It stands
 * for the realm `waterfall` as the tests of `make test-keycloak` prove it, and decides nothing
 * Keycloak does not: a code is good once, for its verifier; a refresh token, once, rotated at
 * each use (`refreshTokenMaxReuse` 0); a session ended refuses its refresh tokens.
 *
 * `signIn` plays the browser on the sign-in page: it reads the request of `/login`, signs a
 * person in, and gives the query Keycloak sends back to `/auth/callback`.
 */
import { createHash, randomUUID } from "node:crypto";

import { exportJWK, generateKeyPair, SignJWT } from "jose";

import type { Send } from "@/session/provider";
import { FRONT_CLIENT, type SessionSettings } from "@/session/settings";

/** Where the tests place the realm and the front: never reached, every request is answered here. */
export const TEST_SETTINGS: SessionSettings = {
  realmAddress: "https://keycloak.test/auth/realms/waterfall",
  realmBackchannel: "https://keycloak.test/auth/realms/waterfall",
  callback: "https://front.test/auth/callback",
  signedOut: "https://front.test/login",
  clientSecret: "test-only-front-client",
};

/** The access token lives five minutes; the session, two hours of inactivity (WF-SEC-0020). */
const ACCESS_LIFETIME = 300;
const SESSION_LIFETIME = 7200;
const LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout";
const TOKEN_ENDPOINT = `${TEST_SETTINGS.realmBackchannel}/protocol/openid-connect/token`;

interface Grant {
  readonly subject: string;
  readonly session: string;
}

/** What the realm has decided, for a test to read. */
export interface TestRealm {
  /** How the server of Next reaches the realm. */
  readonly send: Send;
  /** Sign a person in from the address `/login` sent the browser to: the query of the return. */
  signIn(address: string, subject: string): string;
  /** End the sessions of a person: her refresh tokens are refused from now on. */
  end(subject: string): void;
  /** A logout token of the back channel for a person, signed by the realm unless told otherwise. */
  logoutToken(
    subject: string,
    claims?: Record<string, unknown>,
    foreign?: boolean,
  ): Promise<string>;
  /** The refresh grants the realm answered, by the refresh token presented. */
  readonly refreshes: string[];
  /** The codes the realm was asked to exchange. */
  readonly codes: string[];
  /** Every token the realm gave, for a test to look for in what the browser receives. */
  readonly issued: string[];
}

/** The form a request of openid-client carries. */
function formOf(body: unknown): URLSearchParams {
  return new URLSearchParams(body instanceof URLSearchParams ? body : String(body));
}

/** A refusal of the token endpoint, as OAuth writes it. */
function refusal(error: string): Response {
  return Response.json({ error }, { status: 400 });
}

/** Make a realm, its keys drawn anew. */
export async function testRealm(): Promise<TestRealm> {
  const { privateKey, publicKey } = await generateKeyPair("RS256");
  const foreign = await generateKeyPair("RS256");
  const jwks = { keys: [{ ...(await exportJWK(publicKey)), kid: "realm", alg: "RS256" }] };
  const codes = new Map<string, Grant & { challenge: string; nonce: string }>();
  const refreshTokens = new Map<string, Grant>();
  const ended = new Set<string>();
  const refreshes: string[] = [];
  const presentedCodes: string[] = [];
  const issued: string[] = [];

  // Issued now, good for five minutes, by the realm, for the front: unless the claims say otherwise.
  const sign = (claims: Record<string, unknown>, key = privateKey) => {
    const now = Math.floor(Date.now() / 1000);
    const issued = { iss: TEST_SETTINGS.realmAddress, aud: FRONT_CLIENT, iat: now, exp: now + 300 };
    return new SignJWT({ ...issued, ...claims })
      .setProtectedHeader({ alg: "RS256", kid: "realm" })
      .sign(key);
  };

  const tokens = async (grant: Grant, nonce?: string) => {
    const refreshToken = randomUUID();
    refreshTokens.set(refreshToken, grant);
    const answer = {
      access_token: `access-${randomUUID()}`,
      refresh_token: refreshToken,
      id_token: await sign({ sub: grant.subject, sid: grant.session, nonce }),
      token_type: "Bearer",
      expires_in: ACCESS_LIFETIME,
      refresh_expires_in: SESSION_LIFETIME,
    };
    issued.push(answer.access_token, answer.refresh_token, answer.id_token);
    return Response.json(answer, { headers: { "Cache-Control": "no-store" } });
  };

  const token = async (form: URLSearchParams) => {
    if (form.get("client_secret") !== TEST_SETTINGS.clientSecret) {
      return refusal("unauthorized_client");
    }
    if (form.get("grant_type") === "refresh_token") {
      const presented = form.get("refresh_token") ?? "";
      refreshes.push(presented);
      const grant = refreshTokens.get(presented);
      refreshTokens.delete(presented);
      return grant === undefined || ended.has(grant.subject)
        ? refusal("invalid_grant")
        : tokens(grant);
    }
    presentedCodes.push(form.get("code") ?? "");
    const code = codes.get(form.get("code") ?? "");
    codes.delete(form.get("code") ?? "");
    const verifier = form.get("code_verifier") ?? "";
    const challenge = createHash("sha256").update(verifier).digest("base64url");
    const valid =
      code?.challenge === challenge && form.get("redirect_uri") === TEST_SETTINGS.callback;
    return code === undefined || !valid ? refusal("invalid_grant") : tokens(code, code.nonce);
  };

  return {
    refreshes,
    codes: presentedCodes,
    issued,
    send: async (url, init) =>
      url === TOKEN_ENDPOINT && init.method === "POST"
        ? token(formOf(init.body))
        : url.endsWith("/certs")
          ? Response.json(jwks)
          : new Response(null, { status: 404 }),

    signIn(address, subject) {
      const request = new URL(address).searchParams;
      const code = randomUUID();
      codes.set(code, {
        subject,
        session: randomUUID(),
        challenge: request.get("code_challenge") ?? "",
        nonce: request.get("nonce") ?? "",
      });
      const back = new URLSearchParams({
        state: request.get("state") ?? "",
        session_state: randomUUID(),
        iss: TEST_SETTINGS.realmAddress,
        code,
      });
      return `?${back.toString()}`;
    },

    end(subject) {
      ended.add(subject);
    },

    logoutToken: (subject, claims = {}, other = false) =>
      sign(
        {
          sub: subject,
          sid: randomUUID(),
          jti: randomUUID(),
          events: { [LOGOUT_EVENT]: {} },
          ...claims,
        },
        other ? foreign.privateKey : privateKey,
      ),
  };
}

package com.phoenix.companion.network;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;

/**
 * Unit tests verifying security controls in SessionAuthenticator.
 */
public class SessionAuthenticatorTest {

    private static final String TEST_TOKEN = "d7a4f910b892301c27df8e04b901cd1f";
    private SessionAuthenticator authenticator;

    @Before
    public void setUp() {
        authenticator = new SessionAuthenticator(TEST_TOKEN);
    }

    @Test
    public void testHandshakeSuccess() throws Exception {
        long timestamp = System.currentTimeMillis();
        String contentToSign = "AUTHENTICATE" + TEST_TOKEN + timestamp;
        String signature = calculateHmacSha256(contentToSign, TEST_TOKEN);

        JSONObject requestJson = new JSONObject();
        requestJson.put("command", "AUTHENTICATE");
        requestJson.put("token", TEST_TOKEN);
        requestJson.put("timestamp", timestamp);
        requestJson.put("signature", signature);

        String resultStr = authenticator.authenticate(requestJson);
        JSONObject resultJson = new JSONObject(resultStr);

        assertEquals("AUTHENTICATED", resultJson.getString("status"));
        assertNotNull(resultJson.getString("sessionId"));
        assertNotNull(authenticator.getActiveSessionId());
    }

    @Test
    public void testHandshakeInvalidToken() throws Exception {
        long timestamp = System.currentTimeMillis();
        String badToken = "wrong_token_value_1234567890abc";
        String contentToSign = "AUTHENTICATE" + badToken + timestamp;
        String signature = calculateHmacSha256(contentToSign, badToken);

        JSONObject requestJson = new JSONObject();
        requestJson.put("command", "AUTHENTICATE");
        requestJson.put("token", badToken);
        requestJson.put("timestamp", timestamp);
        requestJson.put("signature", signature);

        String resultStr = authenticator.authenticate(requestJson);
        JSONObject resultJson = new JSONObject(resultStr);

        assertEquals("UNAUTHORIZED", resultJson.getString("status"));
    }

    @Test
    public void testHandshakeInvalidSignature() throws Exception {
        long timestamp = System.currentTimeMillis();
        JSONObject requestJson = new JSONObject();
        requestJson.put("command", "AUTHENTICATE");
        requestJson.put("token", TEST_TOKEN);
        requestJson.put("timestamp", timestamp);
        requestJson.put("signature", "invalid_signature_hashes_abc");

        String resultStr = authenticator.authenticate(requestJson);
        JSONObject resultJson = new JSONObject(resultStr);

        assertEquals("UNAUTHORIZED", resultJson.getString("status"));
    }

    @Test
    public void testRequestValidationAndReplayProtection() throws Exception {
        // 1. Perform successful handshake
        long timestamp = System.currentTimeMillis();
        String contentToSign = "AUTHENTICATE" + TEST_TOKEN + timestamp;
        String handshakeSig = calculateHmacSha256(contentToSign, TEST_TOKEN);

        JSONObject handshakeJson = new JSONObject();
        handshakeJson.put("command", "AUTHENTICATE");
        handshakeJson.put("token", TEST_TOKEN);
        handshakeJson.put("timestamp", timestamp);
        handshakeJson.put("signature", handshakeSig);

        String authResult = authenticator.authenticate(handshakeJson);
        JSONObject authJson = new JSONObject(authResult);
        String sessionId = authJson.getString("sessionId");

        // 2. Perform Request 1 (Valid sequence: 1)
        JSONObject req1 = new JSONObject();
        req1.put("command", "GET_CONTACTS");
        req1.put("sessionId", sessionId);
        req1.put("sequenceNumber", 1);
        req1.put("timestamp", timestamp + 1000);
        req1.put("signature", authenticator.calculatePayloadSignature(req1, TEST_TOKEN));

        assertTrue(authenticator.validateRequest(req1));

        // 3. Replay Protection: Re-send Request 1 (sequence: 1) -> must fail
        assertFalse(authenticator.validateRequest(req1));

        // 4. Replay Protection: Request with lower sequence (sequence: 0) -> must fail
        JSONObject req2 = new JSONObject();
        req2.put("command", "GET_CONTACTS");
        req2.put("sessionId", sessionId);
        req2.put("sequenceNumber", 0);
        req2.put("timestamp", timestamp + 2000);
        req2.put("signature", authenticator.calculatePayloadSignature(req2, TEST_TOKEN));

        assertFalse(authenticator.validateRequest(req2));

        // 5. Perform Request 3 (Valid sequence: 2) -> must succeed
        JSONObject req3 = new JSONObject();
        req3.put("command", "GET_CONTACTS");
        req3.put("sessionId", sessionId);
        req3.put("sequenceNumber", 2);
        req3.put("timestamp", timestamp + 3000);
        req3.put("signature", authenticator.calculatePayloadSignature(req3, TEST_TOKEN));

        assertTrue(authenticator.validateRequest(req3));
    }

    @Test
    public void testRequestTamperProtection() throws Exception {
        // 1. Perform handshake
        long timestamp = System.currentTimeMillis();
        String contentToSign = "AUTHENTICATE" + TEST_TOKEN + timestamp;
        String handshakeSig = calculateHmacSha256(contentToSign, TEST_TOKEN);

        JSONObject handshakeJson = new JSONObject();
        handshakeJson.put("command", "AUTHENTICATE");
        handshakeJson.put("token", TEST_TOKEN);
        handshakeJson.put("timestamp", timestamp);
        handshakeJson.put("signature", handshakeSig);

        String authResult = authenticator.authenticate(handshakeJson);
        JSONObject authJson = new JSONObject(authResult);
        String sessionId = authJson.getString("sessionId");

        // 2. Build valid Request
        JSONObject req = new JSONObject();
        req.put("command", "GET_CONTACTS");
        req.put("sessionId", sessionId);
        req.put("sequenceNumber", 1);
        req.put("timestamp", timestamp + 1000);
        req.put("signature", authenticator.calculatePayloadSignature(req, TEST_TOKEN));

        // 3. Tamper with request (change value after signing)
        req.put("command", "DELETE_ALL_DATA"); // change command

        // 4. Assert validation fails due to signature mismatch
        assertFalse(authenticator.validateRequest(req));
    }

    private String calculateHmacSha256(String data, String key) throws Exception {
        javax.crypto.spec.SecretKeySpec secretKey = new javax.crypto.spec.SecretKeySpec(key.getBytes("UTF-8"), "HmacSHA256");
        javax.crypto.Mac mac = javax.crypto.Mac.getInstance("HmacSHA256");
        mac.init(secretKey);
        byte[] rawHmac = mac.doFinal(data.getBytes("UTF-8"));
        
        StringBuilder hexString = new StringBuilder();
        for (byte b : rawHmac) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }
}

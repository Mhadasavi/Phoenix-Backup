package com.phoenix.companion.network;

import org.json.JSONException;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Handles session creation, token validation, sequence checks (replay protection),
 * and message integrity signature validation using HMAC-SHA256.
 */
public class SessionAuthenticator {

    private final String expectedToken;
    private String activeSessionId = null;
    private long lastSequenceNumber = -1;

    public SessionAuthenticator(String expectedToken) {
        if (expectedToken == null || expectedToken.trim().isEmpty()) {
            throw new IllegalArgumentException("Expected token cannot be null or empty");
        }
        this.expectedToken = expectedToken;
    }

    public String getActiveSessionId() {
        return activeSessionId;
    }

    /**
     * Authenticates the initial connection handshake.
     *
     * @param requestJson the raw JSON payload from client
     * @return a JSON string indicating authentication status and containing the generated sessionId
     * @throws JSONException if JSON structure is invalid
     */
    public String authenticate(JSONObject requestJson) throws JSONException {
        String command = requestJson.optString("command");
        if (!"AUTHENTICATE".equals(command)) {
            return buildErrorResponse("UNAUTHORIZED", "Handshake must begin with AUTHENTICATE command");
        }

        String clientToken = requestJson.optString("token");
        String signature = requestJson.optString("signature");
        long timestamp = requestJson.optLong("timestamp", 0);

        if (clientToken.isEmpty() || signature.isEmpty() || timestamp == 0) {
            return buildErrorResponse("UNAUTHORIZED", "Missing credentials, timestamp, or signature");
        }

        // Verify token matches expected token
        if (!expectedToken.equals(clientToken)) {
            return buildErrorResponse("UNAUTHORIZED", "Invalid authentication token");
        }

        // Verify handshake signature to guarantee integrity
        String contentToSign = "AUTHENTICATE" + clientToken + timestamp;
        String computedSignature = calculateHmacSha256(contentToSign, expectedToken);

        if (!computedSignature.equals(signature)) {
            return buildErrorResponse("UNAUTHORIZED", "Handshake message integrity check failed");
        }

        // Generate a new secure session ID
        activeSessionId = UUID.randomUUID().toString();
        lastSequenceNumber = 0; // reset sequence numbers for the new session

        JSONObject successResponse = new JSONObject();
        successResponse.put("status", "AUTHENTICATED");
        successResponse.put("sessionId", activeSessionId);
        successResponse.put("message", "Connection established successfully.");
        return successResponse.toString();
    }

    /**
     * Validates a request's session, sequence, and message integrity.
     *
     * @param requestJson the raw JSON request
     * @return true if valid, false otherwise
     */
    public boolean validateRequest(JSONObject requestJson) {
        if (activeSessionId == null) {
            return false;
        }

        String sessionId = requestJson.optString("sessionId");
        long sequenceNumber = requestJson.optLong("sequenceNumber", -1);
        String signature = requestJson.optString("signature");

        if (!activeSessionId.equals(sessionId)) {
            return false; // Invalid session ID
        }

        // Replay Protection: Sequence must be monotonically increasing
        if (sequenceNumber <= lastSequenceNumber) {
            return false;
        }

        // Message Integrity Check: Verify payload HMAC-SHA256 signature
        try {
            String computedSignature = calculatePayloadSignature(requestJson, expectedToken);
            if (!computedSignature.equals(signature)) {
                return false; // Signature mismatch (tampering)
            }
        } catch (Exception e) {
            return false; // Error calculating signature
        }

        // Validated successfully: update sequence tracker
        lastSequenceNumber = sequenceNumber;
        return true;
    }

    /**
     * Generates a signature of the JSON payload excluding the "signature" key.
     * Elements are serialized deterministically by sorting keys alphabetically.
     */
    public String calculatePayloadSignature(JSONObject json, String secretKey) throws JSONException {
        List<String> keys = new ArrayList<>();
        json.keys().forEachRemaining(key -> {
            if (!"signature".equals(key)) {
                keys.add(key);
            }
        });
        Collections.sort(keys);

        StringBuilder dataToSign = new StringBuilder();
        for (String key : keys) {
            dataToSign.append(key).append("=").append(json.opt(key)).append(";");
        }

        return calculateHmacSha256(dataToSign.toString(), secretKey);
    }

    /**
     * Computes HMAC-SHA256 signature of input string.
     */
    private String calculateHmacSha256(String data, String key) {
        try {
            SecretKeySpec secretKey = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(secretKey);
            byte[] rawHmac = mac.doFinal(data.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(rawHmac);
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new RuntimeException("HMAC-SHA256 algorithm failure", e);
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder hexString = new StringBuilder();
        for (byte b : bytes) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }

    private String buildErrorResponse(String status, String message) {
        try {
            JSONObject response = new JSONObject();
            response.put("status", status);
            response.put("message", message);
            return response.toString();
        } catch (JSONException e) {
            return "{\"status\":\"ERROR\",\"message\":\"JSON serialization error\"}";
        }
    }
}

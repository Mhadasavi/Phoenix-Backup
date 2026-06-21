package com.phoenix.companion.network;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.json.JSONObject;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/**
 * Local JVM socket binding tests for SecureTransportServer.
 * Asserts length-prefixed frame exchanges and authentication failure disconnects.
 */
public class SecureTransportServerTest {

    private static final int TEST_PORT = 55551;
    private static final String TEST_TOKEN = "d7a4f910b892301c27df8e04b901cd1f";
    
    private SecureTransportServer server;
    private boolean commandHandled = false;

    @Before
    public void setUp() {
        commandHandled = false;
        
        // Setup simple command handler mocking
        SecureTransportServer.CommandHandler mockHandler = (command, requestJson) -> {
            commandHandled = true;
            return "{\"status\":\"SUCCESS\",\"data\":\"mock_data\"}";
        };

        server = new SecureTransportServer(TEST_PORT, TEST_TOKEN, mockHandler);
        server.start();
        
        // Briefly sleep to let socket thread bind
        try {
            Thread.sleep(200);
        } catch (InterruptedException ignored) {}
    }

    @After
    public void tearDown() {
        if (server != null) {
            server.stop();
        }
    }

    @Test
    public void testServerConnection_FailedAuthentication_Disconnects() throws Exception {
        try (Socket socket = new Socket("127.0.0.1", TEST_PORT);
             DataInputStream in = new DataInputStream(socket.getInputStream());
             DataOutputStream out = new DataOutputStream(socket.getOutputStream())) {
            
            // Send invalid handshake frame
            JSONObject badHandshake = new JSONObject();
            badHandshake.put("command", "AUTHENTICATE");
            badHandshake.put("token", "wrong_token");
            badHandshake.put("timestamp", System.currentTimeMillis());
            badHandshake.put("signature", "bad_signature");

            writeFrame(out, badHandshake.toString());

            // Read response
            String responseStr = readFrame(in);
            JSONObject responseJson = new JSONObject(responseStr);

            assertEquals("UNAUTHORIZED", responseJson.getString("status"));
            
            // Assert that the server closes the connection shortly after sending UNAUTHORIZED
            byte[] buffer = new byte[100];
            int readBytes = socket.getInputStream().read(buffer);
            // If connection closed, read returns -1
            assertEquals(-1, readBytes);
        }
    }

    @Test
    public void testServerConnection_SuccessfulSession() throws Exception {
        try (Socket socket = new Socket("127.0.0.1", TEST_PORT);
             DataInputStream in = new DataInputStream(socket.getInputStream());
             DataOutputStream out = new DataOutputStream(socket.getOutputStream())) {

            long timestamp = System.currentTimeMillis();
            String handshakeSign = calculateHmacSha256("AUTHENTICATE" + TEST_TOKEN + timestamp, TEST_TOKEN);

            // Send valid handshake
            JSONObject handshake = new JSONObject();
            handshake.put("command", "AUTHENTICATE");
            handshake.put("token", TEST_TOKEN);
            handshake.put("timestamp", timestamp);
            handshake.put("signature", handshakeSign);

            writeFrame(out, handshake.toString());

            // Read response
            String responseStr = readFrame(in);
            JSONObject responseJson = new JSONObject(responseStr);

            assertEquals("AUTHENTICATED", responseJson.getString("status"));
            String sessionId = responseJson.getString("sessionId");

            // Build valid request
            JSONObject request = new JSONObject();
            request.put("command", "GET_CONTACTS");
            request.put("sessionId", sessionId);
            request.put("sequenceNumber", 1);
            request.put("timestamp", timestamp + 1000);
            
            // Generate signature using a quick mock-up or the local SHA-256 calculation
            SessionAuthenticator authHelper = new SessionAuthenticator(TEST_TOKEN);
            request.put("signature", authHelper.calculatePayloadSignature(request, TEST_TOKEN));

            writeFrame(out, request.toString());

            // Read request execution response
            String reqResponseStr = readFrame(in);
            JSONObject reqResponseJson = new JSONObject(reqResponseStr);

            assertEquals("SUCCESS", reqResponseJson.getString("status"));
            assertEquals("mock_data", reqResponseJson.getString("data"));
            assertTrue(commandHandled);
        }
    }

    private void writeFrame(DataOutputStream out, String payload) throws IOException {
        byte[] buffer = payload.getBytes(StandardCharsets.UTF_8);
        out.writeInt(buffer.length);
        out.write(buffer);
        out.flush();
    }

    private String readFrame(DataInputStream in) throws IOException {
        int length = in.readInt();
        byte[] buffer = new byte[length];
        in.readFully(buffer);
        return new String(buffer, StandardCharsets.UTF_8);
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

package com.phoenix.companion.network;

import android.util.Log;

import org.json.JSONObject;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;

/**
 * Server daemon that binds strictly to loopback (127.0.0.1) and handles
 * framed, authenticated socket sessions over USB ADB port forwarding.
 */
public class SecureTransportServer implements Runnable {

    private static final String TAG = "PhoenixSecureTransport";
    private final int port;
    private final SessionAuthenticator authenticator;
    private final CommandHandler commandHandler;
    
    private ServerSocket serverSocket;
    private boolean isRunning = false;

    /**
     * Interface to delegate validated commands to the application layer.
     */
    public interface CommandHandler {
        String handleCommand(String command, JSONObject requestJson);
    }

    public SecureTransportServer(int port, String token, CommandHandler commandHandler) {
        this.port = port;
        this.authenticator = new SessionAuthenticator(token);
        this.commandHandler = commandHandler;
    }

    public void start() {
        if (isRunning) return;
        isRunning = true;
        new Thread(this, "SecureTransportServerThread").start();
        Log.i(TAG, "Server initialized targeting port: " + port);
    }

    public void stop() {
        isRunning = false;
        if (serverSocket != null) {
            try {
                serverSocket.close();
                Log.i(TAG, "Server socket closed successfully");
            } catch (IOException e) {
                Log.e(TAG, "Error closing server socket: " + e.getMessage());
            }
        }
    }

    @Override
    public void run() {
        try {
            // Bind to wildcard interface and enforce loopback-only client checks at accept time
            serverSocket = new ServerSocket(port);
            Log.i(TAG, "Server successfully bound to wildcard port: " + port);

            while (isRunning) {
                try {
                    Socket socket = serverSocket.accept();
                    // Configure socket timeout (e.g., 10 seconds) to prevent hung-up connections
                    socket.setSoTimeout(10000);
                    
                    // Enforce local loopback client IP to block any local Wi-Fi or external scans
                    if (socket.getInetAddress() == null || !socket.getInetAddress().isLoopbackAddress()) {
                        Log.w(TAG, "SECURITY ALERT: Non-loopback connection attempt from " + socket.getInetAddress() + " rejected.");
                        socket.close();
                        continue;
                    }
                    
                    Log.i(TAG, "Accepted connection from client: " + socket.getRemoteSocketAddress());
                    
                    // Handle client session on a separate worker thread
                    new Thread(() -> handleClientSession(socket), "ClientSessionThread").start();

                } catch (IOException e) {
                    if (isRunning) {
                        Log.w(TAG, "Socket accept error: " + e.getMessage());
                    }
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Server thread crash: " + e.getMessage());
        } finally {
            isRunning = false;
        }
    }

    private void handleClientSession(Socket socket) {
        try (
            DataInputStream in = new DataInputStream(socket.getInputStream());
            DataOutputStream out = new DataOutputStream(socket.getOutputStream())
        ) {
            // 1. Initial Handshake Authentication
            String handshakePayload = readFrame(in);
            if (handshakePayload == null) {
                Log.w(TAG, "SECURITY ALERT: Empty initial handshake received. Disconnecting.");
                return;
            }

            JSONObject handshakeJson = new JSONObject(handshakePayload);
            String authResult = authenticator.authenticate(handshakeJson);
            
            JSONObject authResponse = new JSONObject(authResult);
            boolean isAuthenticated = "AUTHENTICATED".equals(authResponse.optString("status"));

            // Write authentication result back to client
            writeFrame(out, authResult);

            if (!isAuthenticated) {
                Log.w(TAG, "SECURITY ALERT: Unauthorized client handshake failed. Socket closed.");
                return;
            }

            Log.i(TAG, "Client authenticated successfully. Session ID: " + authenticator.getActiveSessionId());

            // 2. Main Request Execution Loop
            while (isRunning && !socket.isClosed()) {
                try {
                    String frameData = readFrame(in);
                    if (frameData == null) {
                        Log.i(TAG, "Client disconnected gracefully.");
                        break;
                    }

                    JSONObject requestJson = new JSONObject(frameData);

                    // Replay and Message Integrity validation
                    if (!authenticator.validateRequest(requestJson)) {
                        Log.w(TAG, "SECURITY ALERT: Invalid signature or replay attempt detected. Terminating session.");
                        writeFrame(out, buildErrorResponse("UNAUTHORIZED", "Security validation failed."));
                        break;
                    }

                    // Process and delegate command
                    String command = requestJson.optString("command");
                    Log.d(TAG, "Received validated command: " + command);
                    
                    String response = commandHandler.handleCommand(command, requestJson);
                    writeFrame(out, response);

                } catch (SocketTimeoutException e) {
                    Log.w(TAG, "Session timed out due to client inactivity.");
                    break;
                } catch (Exception e) {
                    Log.e(TAG, "Error handling request frame: " + e.getMessage());
                    writeFrame(out, buildErrorResponse("ERROR", "Internal server error processing frame."));
                    break;
                }
            }

        } catch (IOException e) {
            Log.w(TAG, "Session connection closed: " + e.getMessage());
        } catch (Exception e) {
            Log.e(TAG, "Unexpected crash in session thread: " + e.getMessage());
        } finally {
            try {
                socket.close();
                Log.i(TAG, "Client socket cleaned up successfully.");
            } catch (IOException e) {
                Log.w(TAG, "Error closing client socket: " + e.getMessage());
            }
        }
    }

    /**
     * Reads a 4-byte big-endian length prefixed frame, followed by UTF-8 string payload.
     */
    private String readFrame(DataInputStream in) throws IOException {
        try {
            int length = in.readInt();
            if (length <= 0 || length > 10 * 1024 * 1024) { // limit frames to 10MB to prevent heap OOM
                throw new IOException("Invalid frame length header: " + length);
            }
            byte[] buffer = new byte[length];
            in.readFully(buffer);
            return new String(buffer, StandardCharsets.UTF_8);
        } catch (IOException e) {
            return null; // EOF or stream read error
        }
    }

    /**
     * Writes a 4-byte length prefix header followed by the UTF-8 payload.
     */
    private void writeFrame(DataOutputStream out, String payload) throws IOException {
        byte[] buffer = payload.getBytes(StandardCharsets.UTF_8);
        out.writeInt(buffer.length);
        out.write(buffer);
        out.flush();
    }

    private String buildErrorResponse(String status, String message) {
        return "{\"status\":\"" + status + "\",\"message\":\"" + message + "\"}";
    }
}

package com.wuwei.demo.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

/**
 * Username-password login API.
 *
 * POST /api/login  {"username": "test", "password": "123456"}
 *
 * On success returns the credentials encoded as an HTTP Basic
 * "Authorization" header value, which can be used to call /api/hello.
 */
@RestController
public class LoginController {

    private final AuthenticationManager authenticationManager;

    public LoginController(AuthenticationManager authenticationManager) {
        this.authenticationManager = authenticationManager;
    }

    @PostMapping("/api/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody LoginRequest request) {
        try {
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(request.getUsername(), request.getPassword()));

            String raw = request.getUsername() + ":" + request.getPassword();
            String basicToken = Base64.getEncoder().encodeToString(raw.getBytes(StandardCharsets.UTF_8));

            return ResponseEntity.ok(Map.of(
                    "status", "success",
                    "username", authentication.getName(),
                    "message", "Login successful",
                    "authorization", "Basic " + basicToken));
        } catch (AuthenticationException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of(
                    "status", "error",
                    "message", "Invalid username or password"));
        }
    }
}

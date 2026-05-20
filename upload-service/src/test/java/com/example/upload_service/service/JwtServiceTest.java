package com.example.upload_service.service;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class JwtServiceTest {

    private static final String SECRET = "super-secret-jwt-key-change-in-production";

    @Test
    void requireAdminAcceptsValidAdminToken() {
        JwtService jwtService = new JwtService();
        ReflectionTestUtils.setField(jwtService, "jwtSecret", SECRET);

        assertDoesNotThrow(() -> jwtService.requireAdmin("Bearer " + tokenWithRole("ROLE_ADMIN")));
    }

    @Test
    void requireAdminRejectsNonAdminRole() {
        JwtService jwtService = new JwtService();
        ReflectionTestUtils.setField(jwtService, "jwtSecret", SECRET);

        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class,
                () -> jwtService.requireAdmin("Bearer " + tokenWithRole("ROLE_USER"))
        );

        assertEquals(HttpStatus.FORBIDDEN, exception.getStatusCode());
    }

    @Test
    void requireAdminRejectsExpiredToken() {
        JwtService jwtService = new JwtService();
        ReflectionTestUtils.setField(jwtService, "jwtSecret", SECRET);

        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class,
                () -> jwtService.requireAdmin("Bearer " + expiredToken())
        );

        assertEquals(HttpStatus.UNAUTHORIZED, exception.getStatusCode());
    }

    private String tokenWithRole(String role) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject("admin")
                .claim("role", role)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(3600)))
                .signWith(Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }

    private String expiredToken() {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject("admin")
                .claim("role", "ROLE_ADMIN")
                .issuedAt(Date.from(now.minusSeconds(7200)))
                .expiration(Date.from(now.minusSeconds(3600)))
                .signWith(Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }
}

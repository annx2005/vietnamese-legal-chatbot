package com.example.auth_service.service;

import com.example.auth_service.entity.User;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class JwtServiceTest {

    @Test
    void generateTokenBuildsSignedJwtWithSubjectAndRole() {
        JwtService jwtService = new JwtService();
        ReflectionTestUtils.setField(jwtService, "jwtSecret", "super-secret-jwt-key-change-in-production");
        ReflectionTestUtils.setField(jwtService, "expirationSeconds", 3600L);

        User user = new User();
        user.setUsername("admin");
        user.setRole("ROLE_ADMIN");

        String token = jwtService.generateToken(user);
        Claims claims = Jwts.parser()
                .verifyWith(Keys.hmacShaKeyFor("super-secret-jwt-key-change-in-production".getBytes(StandardCharsets.UTF_8)))
                .build()
                .parseSignedClaims(token)
                .getPayload();

        assertNotNull(token);
        assertEquals("admin", claims.getSubject());
        assertEquals("ROLE_ADMIN", claims.get("role", String.class));
        assertNotNull(claims.getIssuedAt());
        assertNotNull(claims.getExpiration());
    }
}

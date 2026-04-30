package com.example.auth_service.service;

import com.example.auth_service.dto.AuthRequest;
import com.example.auth_service.dto.AuthResponse;
import com.example.auth_service.entity.User;
import com.example.auth_service.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;

    public AuthResponse login(AuthRequest request) {
        // Sample implementation logic placeholder
        return AuthResponse.builder()
                .token("sample-jwt-token-for-" + request.getUsername())
                .message("Login successful")
                .build();
    }

    public AuthResponse register(AuthRequest request) {
        if (userRepository.findByUsername(request.getUsername()).isPresent()) {
            throw new RuntimeException("Username already exists");
        }
        User user = User.builder()
                .username(request.getUsername())
                .password(request.getPassword()) // In real app, encode password
                .role("ROLE_USER")
                .build();
        userRepository.save(user);

        return AuthResponse.builder()
                .token("sample-jwt-token-for-" + request.getUsername())
                .message("Registration successful")
                .build();
    }
}

package com.example.upload_service.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI uploadServiceOpenAPI() {
        return new OpenAPI()
                .info(new Info().title("Upload Service API")
                        .description("REST API documentation for Document Upload Service")
                        .version("v1.0.0"));
    }
}

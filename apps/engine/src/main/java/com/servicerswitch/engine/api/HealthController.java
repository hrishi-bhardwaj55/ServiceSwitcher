package com.servicerswitch.engine.api;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    @GetMapping("/health")
    public HealthResponse health() {
        return new HealthResponse("engine", "ok");
    }

    public record HealthResponse(
            @JsonProperty("service") String service,
            @JsonProperty("status") String status) {}
}

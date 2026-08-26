package com.servicerswitch.engine.config;

import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import java.math.BigDecimal;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class JacksonConfig {
  @Bean
  Jackson2ObjectMapperBuilderCustomizer exactDecimalStrings() {
    return builder -> builder.serializerByType(BigDecimal.class, ToStringSerializer.instance);
  }
}

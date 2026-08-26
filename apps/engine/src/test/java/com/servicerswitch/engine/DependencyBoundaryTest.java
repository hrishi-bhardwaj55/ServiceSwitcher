package com.servicerswitch.engine;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import org.junit.jupiter.api.Test;

class DependencyBoundaryTest {
  @Test
  void runtimeClasspathContainsNoLlmClientLibrary() {
    String classpath = System.getProperty("java.class.path").toLowerCase(Locale.ROOT);

    assertThat(classpath)
        .doesNotContain("openai")
        .doesNotContain("anthropic")
        .doesNotContain("langchain")
        .doesNotContain("spring-ai");
  }
}

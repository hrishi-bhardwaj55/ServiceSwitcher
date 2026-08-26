package com.servicerswitch.engine.findings;

import java.math.BigDecimal;
import java.util.List;

public final class FindingSupport {
  private FindingSupport() {}

  public static Severity severity(BigDecimal totalImpact, BigDecimal monthlyImpact) {
    if (monthlyImpact.compareTo(new BigDecimal("100.00")) >= 0
        || totalImpact.compareTo(new BigDecimal("1000.00")) >= 0) {
      return Severity.HIGH;
    }
    if (monthlyImpact.compareTo(new BigDecimal("25.00")) >= 0) {
      return Severity.MEDIUM;
    }
    return Severity.LOW;
  }

  public static Finding finding(
      FindingType type,
      BigDecimal actual,
      BigDecimal servicer,
      BigDecimal difference,
      BigDecimal monthlyImpact,
      String explanation,
      List<Evidence> evidence,
      String action) {
    BigDecimal totalImpact = difference == null ? BigDecimal.ZERO : difference.abs();
    BigDecimal monthly = monthlyImpact == null ? BigDecimal.ZERO : monthlyImpact.abs();
    return new Finding(
        type,
        severity(totalImpact, monthly),
        1.0,
        actual,
        servicer,
        difference,
        monthlyImpact,
        explanation,
        evidence,
        List.of("REG_X_1024_17"),
        action);
  }
}

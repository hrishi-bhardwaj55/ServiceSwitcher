package com.servicerswitch.engine.findings;

import java.util.List;

public final class FindingRegistry {
  private final List<FindingDetector> detectors =
      List.of(
          new EscrowBalanceMismatchDetector(),
          new PropertyTaxProjectionMismatchDetector(),
          new EscrowShortageCalculationErrorDetector(),
          new DuplicateTaxDisbursementDetector(),
          new UnexplainedPaymentIncreaseDetector());

  public List<Finding> evaluate(ReconciliationContext context) {
    return detectors.stream()
        .map(detector -> detector.detect(context))
        .flatMap(java.util.Optional::stream)
        .toList();
  }
}
